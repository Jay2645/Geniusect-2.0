'use strict';

const assert = require('assert');
const util = require('util');

const Dex = require('./../../../Pokemon-Showdown/sim/dex');
const Sim = require('./../../../Pokemon-Showdown/sim');

const cache = new Map();

const RULE_FLAGS = {
	pokemon: 1,
	legality: 2,
	preview: 4,
	sleepClause: 8,
	cancel: 16,
};

function capitalize(word) {
	return word.charAt(0).toUpperCase() + word.slice(1);
}

/**
 * The default random number generator seed used if one is not given.
 */
const DEFAULT_SEED = [0x09917, 0x06924, 0x0e1c8, 0x06af0];

class BattleHelper {
	constructor(options) {
		if (!options) options = {};

		const mod = options.mod || 'base';
		this.baseFormat = options.baseFormat || {effectType: 'Format', mod: mod};
		this.dex = Dex.mod(mod);

		this.modPrefix = this.baseFormat.name ? `[${this.baseFormat.name}]` : '';
		if (!this.modPrefix && !this.dex.isBase) {
			this.modPrefix = (/^gen\d$/.test(mod) ? `[Gen ${this.dex.gen}]` : `[${mod}]`);
		}

		// Handle caches
		this.formats = new Map([['singles', new Map()], ['doubles', new Map()], ['triples', new Map()]]);
		cache.set(this.baseFormat.id || mod, this);
	}

	mod(mod) {
		if (cache.has(mod)) return cache.get(mod);
		if (Dex.dexes[mod]) return new BattleHelper({mod: mod});
		const baseFormat = Dex.getFormat(mod);
		if (baseFormat.effectType === 'Format') return new BattleHelper({mod: baseFormat.mod, baseFormat});
		throw new Error(`Mod ${mod} does not exist`);
	}

	gen(genNum) {
		return this.mod('gen' + genNum);
	}

	getFormat(options) {
		let mask = 0;
		for (let property in options) {
			if (property === 'gameType' || !options[property]) continue;
			mask |= RULE_FLAGS[property];
		}
		const gameType = Dex.getId(options.gameType || 'singles');
		if (this.formats.get(gameType).has(mask)) return this.formats.get(gameType).get(mask);

		const gameTypePrefix = gameType === 'singles' ? '' : capitalize(gameType);
		const formatName = [this.modPrefix, gameTypePrefix, "Custom Game", '' + mask].filter(part => part).join(" ");
		const formatId = Dex.getId(formatName);

		const format = Object.assign(Object.assign({}, this.baseFormat), {
			id: formatId,
			name: formatName,

			mask: mask,
			gameType: options.gameType || 'singles',
			isCustomGameFormat: true,

			rated: false,
		});
		if (!format.ruleset) format.ruleset = [];
		if (!format.banlist) format.banlist = [];

		if (options.pokemon) format.ruleset.push('Pokemon');
		if (options.legality) format.banlist.push('Illegal', 'Unreleased');
		if (options.preview) format.ruleset.push('Team Preview');
		if (options.sleepClause) format.ruleset.push('Sleep Clause Mod');
		if (options.cancel) format.ruleset.push('Cancel Mod');

		this.dex.installFormat(formatId, format);
		return format;
	}

	/**
	 * Creates a new Battle and returns it.
	 *
	 * @param {Object} [options]
	 * @param {Team[]} [teams]
	 * @returns {Sim.Battle} A battle.
	 */
	createBattle(options, teams) {
		if (Array.isArray(options)) {
			teams = options;
			options = {};
		}
		if (!options) options = {};
		const format = this.getFormat(options);
		const battle = new Sim.Battle({
			formatid: format.id,
			// If a seed for the pseudo-random number generator is not provided,
			// a default seed (guaranteed to be the same across test executions)
			// will be used.
			seed: options.seed || DEFAULT_SEED,
		});
		
		if (teams) {
			for (let i = 0; i < teams.length; i++) {
				assert(Array.isArray(teams[i]), "Team provided is not an array");
				const slotNum = i + 1;
				battle.join('p' + slotNum, 'Guest ' + slotNum, 1, teams[i]);
			}
        }

        // Note: cache should not be re-used by repeated calls to JSON.stringify.
        var cache = [];
        var battleJson = JSON.stringify(battle, function (key, value) {
            if (typeof value === 'object' && value !== null) {
                if (cache.indexOf(value) !== -1) {
                    // Duplicate reference found
                    try {
                        // If this value does not reference a parent it can be deduped
                        return JSON.parse(JSON.stringify(value));
                    } catch (error) {
                        // discard key if value cannot be deduped
                        return;
                    }
                }
                // Store value in our collection
                cache.push(value);
            }
            return value;
        });
        cache = null; // Enable garbage collection
        return battleJson;
    }
}

const common = exports = module.exports = new BattleHelper();
cache.set('base', common);
cache.set('gen7', common);
