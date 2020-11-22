#!/usr/bin/env python3

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re
import tempfile

import numpy as np
import six

from tensorflow.python.distribute import distribute_coordinator_context as dc_context
from tensorflow.python.eager import context
from tensorflow.python.framework import ops
from tensorflow.python.keras import backend as K
from tensorflow.python.keras.distribute import multi_worker_training_state
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import summary_ops_v2
from tensorflow.python.platform import tf_logging as logging
from tensorflow.python.training import checkpoint_management

from rl.callbacks import Callback

class TensorBoard(Callback):
  # pylint: disable=line-too-long
  """Enable visualizations for TensorBoard.

  TensorBoard is a visualization tool provided with TensorFlow.

  This callback logs events for TensorBoard, including:
  * Metrics summary plots
  * Training graph visualization
  * Activation histograms
  * Sampled profiling

  If you have installed TensorFlow with pip, you should be able
  to launch TensorBoard from the command line:

  ```sh
  tensorboard --logdir=path_to_your_logs
  ```

  You can find more information about TensorBoard
  [here](https://www.tensorflow.org/get_started/summaries_and_tensorboard).

  Arguments:
      log_dir: the path of the directory where to save the log files to be
        parsed by TensorBoard.
      histogram_freq: frequency (in epochs) at which to compute activation and
        weight histograms for the layers of the model. If set to 0, histograms
        won't be computed. Validation data (or split) must be specified for
        histogram visualizations.
      write_graph: whether to visualize the graph in TensorBoard. The log file
        can become quite large when write_graph is set to True.
      write_images: whether to write model weights to visualize as image in
        TensorBoard.
      update_freq: `'batch'` or `'epoch'` or integer. When using `'batch'`,
        writes the losses and metrics to TensorBoard after each batch. The same
        applies for `'epoch'`. If using an integer, let's say `1000`, the
        callback will write the metrics and losses to TensorBoard every 1000
        samples. Note that writing too frequently to TensorBoard can slow down
        your training.
      profile_batch: Profile the batch to sample compute characteristics. By
        default, it will profile the second batch. Set profile_batch=0 to
        disable profiling. Must run in TensorFlow eager mode.
      embeddings_freq: frequency (in epochs) at which embedding layers will
        be visualized. If set to 0, embeddings won't be visualized.
      embeddings_metadata: a dictionary which maps layer name to a file name in
        which metadata for this embedding layer is saved. See the
        [details](
          https://www.tensorflow.org/how_tos/embedding_viz/#metadata_optional)
        about metadata files format. In case if the same metadata file is
        used for all embedding layers, string can be passed.

  Raises:
      ValueError: If histogram_freq is set and no validation data is provided.
  """

  # pylint: enable=line-too-long

  def __init__(self,
               log_dir='logs',
               histogram_freq=0,
               write_graph=True,
               write_images=False,
               update_freq='epoch',
               profile_batch=2,
               embeddings_freq=0,
               embeddings_metadata=None,
               **kwargs):
    super(TensorBoard, self).__init__()
    self._validate_kwargs(kwargs)

    self.log_dir = log_dir
    self.histogram_freq = histogram_freq
    self.write_graph = write_graph
    self.write_images = write_images
    if update_freq == 'batch':
      self.update_freq = 1
    else:
      self.update_freq = update_freq
    self.embeddings_freq = embeddings_freq
    self.embeddings_metadata = embeddings_metadata

    self._samples_seen = 0
    self._samples_seen_at_last_write = 0
    self._current_batch = 0
    self._total_batches_seen = 0
    self._total_val_batches_seen = 0

    # A collection of file writers currently in use, to be closed when
    # training ends for this callback. Writers are keyed by the
    # directory name under the root logdir: e.g., "train" or
    # "validation".
    self._writers = {}
    self._train_run_name = 'train'
    self._validation_run_name = 'validation'

    self._profile_batch = profile_batch
    # True when a trace is running.
    self._is_tracing = False

    # TensorBoard should only write summaries on the chief when in a
    # Multi-Worker setting.
    self._chief_worker_only = True

  def _validate_kwargs(self, kwargs):
    """Handle arguments were supported in V1."""
    if kwargs.get('write_grads', False):
      logging.warning('`write_grads` will be ignored in TensorFlow 2.0 '
                      'for the `TensorBoard` Callback.')
    if kwargs.get('batch_size', False):
      logging.warning('`batch_size` is no longer needed in the '
                      '`TensorBoard` Callback and will be ignored '
                      'in TensorFlow 2.0.')
    if kwargs.get('embeddings_layer_names', False):
      logging.warning('`embeddings_layer_names` is not supported in '
                      'TensorFlow 2.0. Instead, all `Embedding` layers '
                      'will be visualized.')
    if kwargs.get('embeddings_data', False):
      logging.warning('`embeddings_data` is not supported in TensorFlow '
                      '2.0. Instead, all `Embedding` variables will be '
                      'visualized.')

    unrecognized_kwargs = set(kwargs.keys()) - {
        'write_grads', 'embeddings_layer_names', 'embeddings_data', 'batch_size'
    }

    # Only allow kwargs that were supported in V1.
    if unrecognized_kwargs:
      raise ValueError('Unrecognized arguments in `TensorBoard` '
                       'Callback: ' + str(unrecognized_kwargs))

  def set_model(self, model):
    """Sets Keras model and writes graph if specified."""
    self.model = model.model
    with context.eager_mode():
      self._close_writers()
      if self.write_graph:
        with self._get_writer(self._train_run_name).as_default():
          with summary_ops_v2.always_record_summaries():
            if not self.model.run_eagerly:
              summary_ops_v2.graph(K.get_graph(), step=0)

            summary_writable = (
                self.model._is_graph_network or  # pylint: disable=protected-access
                self.model.__class__.__name__ == 'Sequential')  # pylint: disable=protected-access
            if summary_writable:
              summary_ops_v2.keras_model('keras', self.model, step=0)

    if self.embeddings_freq:
      self._configure_embeddings()

  def _configure_embeddings(self):
    """Configure the Projector for embeddings."""
    # TODO(omalleyt): Add integration tests.
    from tensorflow.python.keras.layers import embeddings
    try:
      from tensorboard.plugins import projector
    except ImportError:
      raise ImportError('Failed to import TensorBoard. Please make sure that '
                        'TensorBoard integration is complete."')
    config = projector.ProjectorConfig()
    for layer in self.model.layers:
      if isinstance(layer, embeddings.Embedding):
        embedding = config.embeddings.add()
        embedding.tensor_name = layer.embeddings.name

        if self.embeddings_metadata is not None:
          if isinstance(self.embeddings_metadata, str):
            embedding.metadata_path = self.embeddings_metadata
          else:
            if layer.name in embedding.metadata_path:
              embedding.metadata_path = self.embeddings_metadata.pop(layer.name)

    if self.embeddings_metadata:
      raise ValueError('Unrecognized `Embedding` layer names passed to '
                       '`keras.callbacks.TensorBoard` `embeddings_metadata` '
                       'argument: ' + str(self.embeddings_metadata.keys()))

    class DummyWriter(object):
      """Dummy writer to conform to `Projector` API."""

      def __init__(self, logdir):
        self.logdir = logdir

      def get_logdir(self):
        return self.logdir

    writer = DummyWriter(self.log_dir)
    projector.visualize_embeddings(writer, config)

  def _close_writers(self):
    """Close all remaining open file writers owned by this callback.

    If there are no such file writers, this is a no-op.
    """
    with context.eager_mode():
      for writer in six.itervalues(self._writers):
        writer.close()
      self._writers.clear()

  def _get_writer(self, writer_name):
    """Get a summary writer for the given subdirectory under the logdir.

    A writer will be created if it does not yet exist.

    Arguments:
      writer_name: The name of the directory for which to create or
        retrieve a writer. Should be either `self._train_run_name` or
        `self._validation_run_name`.

    Returns:
      A `SummaryWriter` object.
    """
    if writer_name not in self._writers:
      path = os.path.join(self.log_dir, writer_name)
      writer = summary_ops_v2.create_file_writer_v2(path)
      self._writers[writer_name] = writer
    return self._writers[writer_name]

  def on_train_begin(self, logs=None):
    if self._profile_batch == 1:
      summary_ops_v2.trace_on(graph=True, profiler=True)
      self._is_tracing = True

  def on_batch_end(self, batch, logs=None):
    """Writes scalar summaries for metrics on every training batch.

    Performs profiling if current batch is in profiler_batches.

    Arguments:
      batch: Integer, index of batch within the current epoch.
      logs: Dict. Metric results for this batch.
    """
    # Don't output batch_size and batch number as TensorBoard summaries
    logs = logs or {}
    self._samples_seen += logs.get('size', 1)
    samples_seen_since = self._samples_seen - self._samples_seen_at_last_write
    if self.update_freq != 'epoch' and samples_seen_since >= self.update_freq:
      self._log_metrics(logs, prefix='batch_', step=self._total_batches_seen)
      self._samples_seen_at_last_write = self._samples_seen
    self._total_batches_seen += 1
    if self._is_tracing:
      self._log_trace()
    elif (not self._is_tracing and
          self._total_batches_seen == self._profile_batch - 1):
      self._enable_trace()

  def on_epoch_end(self, epoch, logs=None):
    """Runs metrics and histogram summaries at epoch end."""
    step = epoch if self.update_freq == 'epoch' else self._samples_seen
    self._log_metrics(logs, prefix='epoch_', step=step)

    if self.histogram_freq and epoch % self.histogram_freq == 0:
      self._log_weights(epoch)

    if self.embeddings_freq and epoch % self.embeddings_freq == 0:
      self._log_embeddings(epoch)

  def on_train_end(self, logs=None):
    if self._is_tracing:
      self._log_trace()
    self._close_writers()

  def _enable_trace(self):
    if context.executing_eagerly():
      summary_ops_v2.trace_on(graph=True, profiler=True)
      self._is_tracing = True

  def _log_trace(self):
    if context.executing_eagerly():
      with self._get_writer(self._train_run_name).as_default(), \
          summary_ops_v2.always_record_summaries():
        # TODO(b/126388999): Remove step info in the summary name.
        summary_ops_v2.trace_export(
            name='batch_%d' % self._total_batches_seen,
            step=self._total_batches_seen,
            profiler_outdir=os.path.join(self.log_dir, 'train'))
      self._is_tracing = False

  def _log_metrics(self, logs, prefix, step):
    """Writes metrics out as custom scalar summaries.

    Arguments:
        logs: Dict. Keys are scalar summary names, values are NumPy scalars.
        prefix: String. The prefix to apply to the scalar summary names.
        step: Int. The global step to use for TensorBoard.
    """
    if logs is None:
      logs = {}

    # Group metrics by the name of their associated file writer. Values
    # are lists of metrics, as (name, scalar_value) pairs.
    logs_by_writer = {
        self._train_run_name: [],
        self._validation_run_name: [],
    }
    validation_prefix = 'val_'
    for (name, value) in logs.items():
      if name in ('batch', 'size', 'num_steps'):
        # Scrub non-metric items.
        continue
      if name.startswith(validation_prefix):
        name = name[len(validation_prefix):]
        writer_name = self._validation_run_name
      else:
        writer_name = self._train_run_name
      name = prefix + name  # assign batch or epoch prefix
      logs_by_writer[writer_name].append((name, value))

    with context.eager_mode():
      with summary_ops_v2.always_record_summaries():
        for writer_name in logs_by_writer:
          these_logs = logs_by_writer[writer_name]
          if not these_logs:
            # Don't create a "validation" events file if we don't
            # actually have any validation data.
            continue
          writer = self._get_writer(writer_name)
          with writer.as_default():
            for (name, value) in these_logs:
              summary_ops_v2.scalar(name, value, step=step)

  def _log_weights(self, epoch):
    """Logs the weights of the Model to TensorBoard."""
    writer = self._get_writer(self._train_run_name)
    with context.eager_mode(), \
          writer.as_default(), \
          summary_ops_v2.always_record_summaries():
      for layer in self.model.layers:
        for weight in layer.weights:
          weight_name = weight.name.replace(':', '_')
          with ops.init_scope():
            weight = K.get_value(weight)
          summary_ops_v2.histogram(weight_name, weight, step=epoch)
          if self.write_images:
            self._log_weight_as_image(weight, weight_name, epoch)
      writer.flush()

  def _log_weight_as_image(self, weight, weight_name, epoch):
    """Logs a weight as a TensorBoard image."""
    w_img = array_ops.squeeze(weight)
    shape = K.int_shape(w_img)
    if len(shape) == 1:  # Bias case
      w_img = array_ops.reshape(w_img, [1, shape[0], 1, 1])
    elif len(shape) == 2:  # Dense layer kernel case
      if shape[0] > shape[1]:
        w_img = array_ops.transpose(w_img)
        shape = K.int_shape(w_img)
      w_img = array_ops.reshape(w_img, [1, shape[0], shape[1], 1])
    elif len(shape) == 3:  # ConvNet case
      if K.image_data_format() == 'channels_last':
        # Switch to channels_first to display every kernel as a separate
        # image.
        w_img = array_ops.transpose(w_img, perm=[2, 0, 1])
        shape = K.int_shape(w_img)
      w_img = array_ops.reshape(w_img, [shape[0], shape[1], shape[2], 1])

    shape = K.int_shape(w_img)
    # Not possible to handle 3D convnets etc.
    if len(shape) == 4 and shape[-1] in [1, 3, 4]:
      summary_ops_v2.image(weight_name, w_img, step=epoch)

  def _log_embeddings(self, epoch):
    embeddings_ckpt = os.path.join(self.log_dir, 'train',
                                   'keras_embedding.ckpt-{}'.format(epoch))
    self.model.save_weights(embeddings_ckpt)

class ModelCheckpoint(Callback):
  """Save the model after every epoch.

  `filepath` can contain named formatting options,
  which will be filled the value of `epoch` and
  keys in `logs` (passed in `on_epoch_end`).

  For example: if `filepath` is `weights.{epoch:02d}-{val_loss:.2f}.hdf5`,
  then the model checkpoints will be saved with the epoch number and
  the validation loss in the filename.

  Arguments:
      filepath: string, path to save the model file.
      monitor: quantity to monitor.
      verbose: verbosity mode, 0 or 1.
      save_best_only: if `save_best_only=True`, the latest best model according
        to the quantity monitored will not be overwritten.
      mode: one of {auto, min, max}. If `save_best_only=True`, the decision to
        overwrite the current save file is made based on either the maximization
        or the minimization of the monitored quantity. For `val_acc`, this
        should be `max`, for `val_loss` this should be `min`, etc. In `auto`
        mode, the direction is automatically inferred from the name of the
        monitored quantity.
      save_weights_only: if True, then only the model's weights will be saved
        (`model.save_weights(filepath)`), else the full model is saved
        (`model.save(filepath)`).
      save_freq: `'epoch'` or integer. When using `'epoch'`, the callback saves
        the model after each epoch. When using integer, the callback saves the
        model at end of a batch at which this many samples have been seen since
        last saving. Note that if the saving isn't aligned to epochs, the
        monitored metric may potentially be less reliable (it could reflect as
        little as 1 batch, since the metrics get reset every epoch). Defaults to
        `'epoch'`
      load_weights_on_restart: Whether the training should restore the model. If
        True, the model will attempt to load the checkpoint file from `filepath`
        at the start of `model.fit()`. This saves the need of manually calling
        `model.load_weights()` before `model.fit(). In multi-worker distributed
        training, this provides fault-tolerance and loads the model
        automatically upon recovery of workers. The callback gives up loading if
        the filepath does not exist, and raises ValueError if format does not
        match. Defaults to False.
      **kwargs: Additional arguments for backwards compatibility. Possible key
        is `period`.
  """

  def __init__(self,
               filepath,
               monitor='val_loss',
               verbose=0,
               save_best_only=False,
               save_weights_only=False,
               mode='auto',
               save_freq='epoch',
               load_weights_on_restart=False,
               **kwargs):
    super(ModelCheckpoint, self).__init__()
    self.monitor = monitor
    self.verbose = verbose
    self.filepath = filepath
    self.save_best_only = save_best_only
    self.save_weights_only = save_weights_only
    self.save_freq = save_freq
    self.load_weights_on_restart = load_weights_on_restart
    self.epochs_since_last_save = 0
    self._samples_seen_since_last_saving = 0
    self.metrics = []
    self.infos = []
    self.info_names = None
    
    # Deprecated field `period` is for the number of epochs between which
    # the model is saved.
    if 'period' in kwargs:
      self.period = kwargs['period']
      logging.warning('`period` argument is deprecated. Please use `save_freq` '
                      'to specify the frequency in number of samples seen.')
    else:
      self.period = 1

    if mode not in ['auto', 'min', 'max']:
      logging.warning('ModelCheckpoint mode %s is unknown, '
                      'fallback to auto mode.', mode)
      mode = 'auto'

    if mode == 'min':
      self.monitor_op = np.less
      self.best = np.Inf
    elif mode == 'max':
      self.monitor_op = np.greater
      self.best = -np.Inf
    else:
      if 'acc' in self.monitor or self.monitor.startswith('fmeasure'):
        self.monitor_op = np.greater
        self.best = -np.Inf
      else:
        self.monitor_op = np.less
        self.best = np.Inf

    if self.save_freq != 'epoch' and not isinstance(self.save_freq, int):
      raise ValueError('Unrecognized save_freq: {}'.format(self.save_freq))

    # Only the chief worker writes model checkpoints, but all workers
    # restore checkpoint at on_train_begin().
    self._chief_worker_only = False

  def set_model(self, model):
    self.model = model
    # Use name matching rather than `isinstance` to avoid circular dependencies.
    if (not self.save_weights_only and
        not model._is_graph_network and  # pylint: disable=protected-access
        model.__class__.__name__ != 'Sequential'):
      self.save_weights_only = True

  def on_train_begin(self, logs=None):
    if K.in_multi_worker_mode():
      # pylint: disable=protected-access
      # MultiWorkerTrainingState is used to manage the training state needed
      # for preemption-recovery of a worker in multi-worker training.
      self.model._training_state = (
          multi_worker_training_state.MultiWorkerTrainingState(
              self.model, self.filepath))
      self._training_state = self.model._training_state
      if self._training_state.restore():
        # If the training state needs to be and is successfully restored,
        # it is recovering from a previous failure (or preemption). In such
        # case, do not load the weights from user specified file path.
        return

    # If this is not multi worker training, restoring is not needed, or
    # restoring failed, check if it should load weights on restart.
    # TODO(rchao): Also restore the epoch in single-worker training when
    # `self.load_weights_on_restart=True`.
    if self.load_weights_on_restart:
      # In multi worker training, it only should if `experimental_should_init`
      # is True.
      # TODO(rchao): Reference `experimental_should_init` api from a util file.
      if not K.in_multi_worker_mode() or dc_context.get_current_worker_context(
      ).experimental_should_init:
        filepath_to_load = (
            self._get_most_recently_modified_file_matching_pattern(
                self.filepath))
        if filepath_to_load is not None and os.path.exists(filepath_to_load):
          try:
            # `filepath` may contain placeholders such as `{epoch:02d}`, and
            # thus it attempts to load the most recently modified file with file
            # name matching the pattern.
            self.model.load_weights(filepath_to_load)
          except (IOError, ValueError) as e:
            raise ValueError('Error loading file from {}. Reason: {}'.format(
                filepath_to_load, e))

  def on_train_end(self, logs=None):
    if K.in_multi_worker_mode():
      # In multi-worker training, on successful exit of training, delete the
      # training state backup file that was saved for the purpose of worker
      # recovery.
      self._training_state.delete_backup()
      # Restore the training state so the model is ready for next (possible)
      # multi worker training.
      del self._training_state
      del self.model._training_state

  def on_batch_end(self, batch, logs=None):
    logs = logs or {}
    if isinstance(self.save_freq, int):
      self._samples_seen_since_last_saving += logs.get('size', 1)
      if self._samples_seen_since_last_saving >= self.save_freq:
        self._save_model(epoch=self._current_epoch, logs=logs)
        self._samples_seen_since_last_saving = 0

  def on_epoch_begin(self, epoch, logs=None):
    self._current_epoch = epoch

  def on_epoch_end(self, epoch, logs=None):
    self.epochs_since_last_save += 1
    if self.save_freq == 'epoch':
      self._save_model(epoch=epoch, logs=logs)
    if K.in_multi_worker_mode():
      # For multi-worker training, back up the weights and current training
      # state for possible future recovery.
      # TODO(rchao): Call `back_up` at finer period such as N steps.
      self._training_state.back_up(epoch)

  def on_step_end(self, step, logs):
    if self.info_names is None:
      self.info_names = logs['info'].keys()

    self.metrics.append(logs['metrics'])
    if len(self.info_names) > 0:
      self.infos.append([logs['info'][k] for k in logs['info'].keys()])

  def _save_model(self, epoch, logs):
    """Saves the model.

    Arguments:
        epoch: the epoch this iteration is in.
        logs: the `logs` dict passed in to `on_batch_end` or `on_epoch_end`.
    """
    logs = logs or {}

    if isinstance(self.save_freq,
                  int) or self.epochs_since_last_save >= self.period:
      self.epochs_since_last_save = 0
      file_handle, filepath = self._get_file_handle_and_path(epoch, logs)

      if self.save_best_only:
        current = logs.get(self.monitor)
        if current is None:
          logging.warning('Can save best model only with %s available, '
                          'skipping.', self.monitor)
        else:
          if self.monitor_op(current, self.best):
            if self.verbose > 0:
              print('\nEpoch %05d: %s improved from %0.5f to %0.5f,'
                    ' saving model to %s' % (epoch + 1, self.monitor, self.best,
                                             current, filepath))
            self.best = current
            if self.save_weights_only:
              self.model.save_weights(filepath, overwrite=True)
            else:
              self.model.save(filepath, overwrite=True)
          else:
            if self.verbose > 0:
              print('\nEpoch %05d: %s did not improve from %0.5f' %
                    (epoch + 1, self.monitor, self.best))
      else:
        if self.verbose > 0:
          print('\nEpoch %05d: saving model to %s' % (epoch + 1, filepath))
        if self.save_weights_only:
          self.model.save_weights(filepath, overwrite=True)
        else:
          self.model.save(filepath, overwrite=True)

      self._maybe_remove_file(file_handle, filepath)

  def _get_file_handle_and_path(self, epoch, logs):
    """Returns the file handle and path."""
    # TODO(rchao): Replace dc_context reference with
    # distributed_training_utils.should_current_worker_checkpoint() once
    # distributed_training_utils.py no longer depends on callbacks.py.
    if not K.in_multi_worker_mode() or dc_context.get_current_worker_context(
    ).should_checkpoint:
      return None, self.filepath.format(epoch=epoch + 1, **logs)
    else:
      # If this is multi-worker training, and this worker should not
      # save checkpoint, we replace the filepath with a dummy filepath so
      # it writes to a file that will be removed at the end of _save_model()
      # call. This is because the SyncOnReadVariable needs to be synced across
      # all the workers in order to be read, and all workers need to initiate
      # that.
      file_handle, temp_file_name = tempfile.mkstemp()
      extension = os.path.splitext(self.filepath)[1]
      return file_handle, temp_file_name + extension

  def _maybe_remove_file(self, file_handle, filepath):
    # Remove the file in multi-worker training where this worker should
    # not checkpoint. It is a dummy file previously saved for sync distributed
    # training.
    if K.in_multi_worker_mode(
    ) and not dc_context.get_current_worker_context().should_checkpoint:
      os.close(file_handle)
      os.remove(filepath)

  def _get_most_recently_modified_file_matching_pattern(self, pattern):
    """Returns the most recently modified filepath matching pattern.

    Pattern may contain python formatting placeholder. If
    `tf.train.latest_checkpoint()` does not return None, use that; otherwise,
    check for most recently modified one that matches the pattern.

    In the rare case where there are more than one pattern-matching file having
    the same modified time that is most recent among all, return the filepath
    that is largest (by `>` operator, lexicographically using the numeric
    equivalents). This provides a tie-breaker when multiple files are most
    recent. Note that a larger `filepath` can sometimes indicate a later time of
    modification (for instance, when epoch/batch is used as formatting option),
    but not necessarily (when accuracy or loss is used). The tie-breaker is
    put in the logic as best effort to return the most recent, and to avoid
    undeterministic result.

    Modified time of a file is obtained with `os.path.getmtime()`.

    This utility function is best demonstrated via an example:

    ```python
    file_pattern = 'f.batch{batch:02d}epoch{epoch:02d}.h5'
    test_dir = self.get_temp_dir()
    path_pattern = os.path.join(test_dir, file_pattern)
    file_paths = [
        os.path.join(test_dir, file_name) for file_name in
        ['f.batch03epoch02.h5', 'f.batch02epoch02.h5', 'f.batch01epoch01.h5']
    ]
    for file_path in file_paths:
      # Write something to each of the files
    self.assertEqual(
        _get_most_recently_modified_file_matching_pattern(path_pattern),
        file_paths[-1])
    ```

    Arguments:
        pattern: The file pattern that may optionally contain python placeholder
            such as `{epoch:02d}`.

    Returns:
        The most recently modified file's full filepath matching `pattern`. If
        `pattern` does not contain any placeholder, this returns the filepath
        that
        exactly matches `pattern`. Returns `None` if no match is found.
    """
    dir_name = os.path.dirname(pattern)
    base_name = os.path.basename(pattern)
    base_name_regex = '^' + re.sub(r'{.*}', r'.*', base_name) + '$'

    # If tf.train.latest_checkpoint tells us there exists a latest checkpoint,
    # use that as it is more robust than `os.path.getmtime()`.
    latest_tf_checkpoint = checkpoint_management.latest_checkpoint(dir_name)
    if latest_tf_checkpoint is not None and re.match(
        base_name_regex, os.path.basename(latest_tf_checkpoint)):
      return latest_tf_checkpoint

    latest_mod_time = 0
    file_path_with_latest_mod_time = None
    n_file_with_latest_mod_time = 0
    file_path_with_largest_file_name = None

    if os.path.exists(dir_name):
      for file_name in os.listdir(dir_name):
        # Only consider if `file_name` matches the pattern.
        if re.match(base_name_regex, file_name):
          file_path = os.path.join(dir_name, file_name)
          mod_time = os.path.getmtime(file_path)
          if (file_path_with_largest_file_name is None or
              file_path > file_path_with_largest_file_name):
            file_path_with_largest_file_name = file_path
          if mod_time > latest_mod_time:
            latest_mod_time = mod_time
            file_path_with_latest_mod_time = file_path
            # In the case a file with later modified time is found, reset
            # the counter for the number of files with latest modified time.
            n_file_with_latest_mod_time = 1
          elif mod_time == latest_mod_time:
            # In the case a file has modified time tied with the most recent,
            # increment the counter for the number of files with latest modified
            # time by 1.
            n_file_with_latest_mod_time += 1

    if n_file_with_latest_mod_time == 1:
      # Return the sole file that has most recent modified time.
      return file_path_with_latest_mod_time
    else:
      # If there are more than one file having latest modified time, return
      # the file path with the largest file name.
      return file_path_with_largest_file_name


class EarlyStopping(Callback):
  """Stop training when a monitored quantity has stopped improving.

  Arguments:
      monitor: Quantity to be monitored.
      min_delta: Minimum change in the monitored quantity
          to qualify as an improvement, i.e. an absolute
          change of less than min_delta, will count as no
          improvement.
      patience: Number of epochs with no improvement
          after which training will be stopped.
      verbose: verbosity mode.
      mode: One of `{"auto", "min", "max"}`. In `min` mode,
          training will stop when the quantity
          monitored has stopped decreasing; in `max`
          mode it will stop when the quantity
          monitored has stopped increasing; in `auto`
          mode, the direction is automatically inferred
          from the name of the monitored quantity.
      baseline: Baseline value for the monitored quantity.
          Training will stop if the model doesn't show improvement over the
          baseline.
      restore_best_weights: Whether to restore model weights from
          the epoch with the best value of the monitored quantity.
          If False, the model weights obtained at the last step of
          training are used.

  Example:

  ```python
  callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=3)
  # This callback will stop the training when there is no improvement in
  # the validation loss for three consecutive epochs.
  model.fit(data, labels, epochs=100, callbacks=[callback],
      validation_data=(val_data, val_labels))
  ```
  """

  def __init__(self,
               monitor='val_loss',
               min_delta=0,
               patience=0,
               verbose=0,
               mode='auto',
               baseline=None,
               restore_best_weights=False):
    super(EarlyStopping, self).__init__()

    self.monitor = monitor
    self.patience = patience
    self.verbose = verbose
    self.baseline = baseline
    self.min_delta = abs(min_delta)
    self.wait = 0
    self.stopped_epoch = 0
    self.restore_best_weights = restore_best_weights
    self.best_weights = None

    if mode not in ['auto', 'min', 'max']:
      logging.warning('EarlyStopping mode %s is unknown, '
                      'fallback to auto mode.', mode)
      mode = 'auto'

    if mode == 'min':
      self.monitor_op = np.less
    elif mode == 'max':
      self.monitor_op = np.greater
    else:
      if 'acc' in self.monitor:
        self.monitor_op = np.greater
      else:
        self.monitor_op = np.less

    if self.monitor_op == np.greater:
      self.min_delta *= 1
    else:
      self.min_delta *= -1

  def on_train_begin(self, logs=None):
    # Allow instances to be re-used
    self.wait = 0
    self.stopped_epoch = 0
    if self.baseline is not None:
      self.best = self.baseline
    else:
      self.best = np.Inf if self.monitor_op == np.less else -np.Inf

  def on_epoch_end(self, epoch, logs=None):
    current = self.get_monitor_value(logs)
    if current is None:
      return
    if self.monitor_op(current - self.min_delta, self.best):
      self.best = current
      self.wait = 0
      if self.restore_best_weights:
        self.best_weights = self.model.get_weights()
    else:
      self.wait += 1
      if self.wait >= self.patience:
        self.stopped_epoch = epoch
        self.model.stop_training = True
        if self.restore_best_weights:
          if self.verbose > 0:
            print('Restoring model weights from the end of the best epoch.')
          self.model.set_weights(self.best_weights)

  def on_train_end(self, logs=None):
    if self.stopped_epoch > 0 and self.verbose > 0:
      print('Epoch %05d: early stopping' % (self.stopped_epoch + 1))

  def get_monitor_value(self, logs):
    logs = logs or {}
    monitor_value = logs.get(self.monitor)
    if monitor_value is None:
      logging.warning('Early stopping conditioned on metric `%s` '
                      'which is not available. Available metrics are: %s',
                      self.monitor, ','.join(list(logs.keys())))
    return monitor_value