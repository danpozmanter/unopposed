import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import type { ElectionData } from './types';

const __dirname = dirname(fileURLToPath(import.meta.url));

function loadElectionData(filename: string): ElectionData | null {
	try {
		const path = join(__dirname, '../../election_data', filename);
		const data = JSON.parse(readFileSync(path, 'utf-8'));
		if (data.error) return null;
		return data;
	} catch {
		return null;
	}
}

function getAllElectionFiles(): string[] {
	const dir = join(__dirname, '../../election_data');
	return readdirSync(dir).filter((f: string) => f.endsWith('.json') && f !== 'manifest.json');
}

function countUniqueRacesByParty(data: ElectionData): Record<string, number> {
	const racesByParty: Record<string, Set<string>> = {};
	for (const c of data.unopposed_candidates) {
		const raceKey = `${c.office}:${c.district}`;
		if (!racesByParty[c.party]) {
			racesByParty[c.party] = new Set();
		}
		racesByParty[c.party].add(raceKey);
	}
	const counts: Record<string, number> = {};
	for (const [party, races] of Object.entries(racesByParty)) {
		counts[party] = races.size;
	}
	return counts;
}

describe('Data integrity: unopposed never exceeds total by party', () => {
	const files = getAllElectionFiles();

	for (const file of files) {
		it(`${file}: unopposed races by party <= total races by party`, () => {
			const data = loadElectionData(file);
			if (!data) return;

			const unopposedByParty = countUniqueRacesByParty(data);

			for (const [party, unopposedCount] of Object.entries(unopposedByParty)) {
				const totalForParty = data.total_races_by_party?.[party] || 0;
				expect(
					unopposedCount,
					`${file}: ${party} has ${unopposedCount} unopposed but only ${totalForParty} total`
				).toBeLessThanOrEqual(totalForParty);
			}
		});
	}
});

describe('Data integrity: basic checks', () => {
	it('MA 2026: total field equals candidate count', () => {
		const ma = loadElectionData('massachusetts_2026.json');
		if (!ma) return;
		expect(ma.total).toBe(ma.unopposed_candidates.length);
	});

	it('VA 2025: total field equals candidate count', () => {
		const va = loadElectionData('virginia_2025.json');
		if (!va) return;
		expect(va.total).toBe(va.unopposed_candidates.length);
	});
});

describe('Data integrity: general/primary stats (when present)', () => {
	const files = getAllElectionFiles();

	for (const file of files) {
		it(`${file}: general.total_unopposed <= general.total_races`, () => {
			const data = loadElectionData(file);
			if (!data?.general) return;

			expect(
				data.general.total_unopposed,
				`${file}: general unopposed (${data.general.total_unopposed}) exceeds total races (${data.general.total_races})`
			).toBeLessThanOrEqual(data.general.total_races);
		});

		it(`${file}: primary unopposed by party <= primary total races by party`, () => {
			const data = loadElectionData(file);
			if (!data?.primary) return;

			for (const [party, unopposedCount] of Object.entries(data.primary.unopposed_by_party)) {
				const totalForParty = data.primary.total_races_by_party?.[party] || 0;
				expect(
					unopposedCount,
					`${file}: ${party} primary has ${unopposedCount} unopposed but only ${totalForParty} total races`
				).toBeLessThanOrEqual(totalForParty);
			}
		});
	}
});
