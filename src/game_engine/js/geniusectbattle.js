/**
 * Simulator GeniusectBattle
 * Pokemon Showdown - http://pokemonshowdown.com/
 *
 * @license MIT
 */
'use strict';

const Dex = require('./../../../Pokemon-Showdown/sim/dex');
const Sim = require('./../../../Pokemon-Showdown/sim');
global.toId = Dex.getId;
const Data = require('./../../../Pokemon-Showdown/sim/dex-data');
const PRNG = require('./../../../Pokemon-Showdown/sim/prng');
const Side = require('./../../../Pokemon-Showdown/sim/side');
const Pokemon = require('./../../../Pokemon-Showdown/sim/pokemon');

/**
 * An object representing a Pokemon that has fainted
 *
 * @typedef {Object} FaintedPokemon
 * @property {Pokemon} target
 * @property {Pokemon?} source
 * @property {Effect?} effect
 */

/**
 * @typedef {Object} PlayerOptions
 * @property {string} [name]
 * @property {string} [avatar]
 * @property {string | PokemonSet[]?} [team]
 */
/**
 * @typedef {Object} BattleOptions
 * @property {string} formatid Format ID
 * @property {(type: string, data: string | string[]) => void} [send] Output callback
 * @property {PRNG} [prng] PRNG override (you usually don't need this, just pass a seed)
 * @property {[number, number, number, number]} [seed] PRNG seed
 * @property {boolean | string} [rated] Rated string
 * @property {PlayerOptions} [p1] Player 1 data
 * @property {PlayerOptions} [p2] Player 2 data
 */

class GeniusectBattle extends Sim.Battle {
	/**
	 * @param {'p1' | 'p2'} slot
	 * @param {PlayerOptions} options
	 */
    setPlayer(slot, options) {
        let side;
        // create player
        const slotNum = (slot === 'p2' ? 1 : 0);
        const team = this.getTeam(options.team || null);
        side = new Side(options.name || `Player ${slotNum + 1}`, this, slotNum, team);
        if (options.avatar) side.avatar = '' + options.avatar;
        this[slot] = side;
        this.sides[slotNum] = side;
    }
}

module.exports = GeniusectBattle;
