import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import type { ElectionData } from './types';

function loadElectionData(filename: string): ElectionData {
	const path = join(__dirname, '../../election_data', filename);
	return JSON.parse(readFileSync(path, 'utf-8'));
}

function calculateSummary(electionsByState: Map<string, ElectionData | null>) {
	let totalUnopposed = 0;
	let totalRaces = 0;
	const countByParty: Record<string, number> = {};
	const totalByParty: Record<string, number> = {};

	for (const electionData of electionsByState.values()) {
		if (electionData?.unopposed_candidates) {
			totalRaces += electionData.total_races || 0;
			totalUnopposed += electionData.total || 0;
			for (const candidate of electionData.unopposed_candidates) {
				const party = candidate.party;
				countByParty[party] = (countByParty[party] || 0) + 1;
			}
			if (electionData.total_races_by_party) {
				for (const [party, count] of Object.entries(electionData.total_races_by_party)) {
					totalByParty[party] = (totalByParty[party] || 0) + count;
				}
			}
		}
	}

	return { totalUnopposed, totalRaces, countByParty, totalByParty };
}

describe('Summary calculations', () => {
	it('counts all unopposed candidates for MA 2026', () => {
		const ma = loadElectionData('massachusetts_2026.json');
		const map = new Map<string, ElectionData | null>([['MA', ma]]);
		const summary = calculateSummary(map);

		expect(summary.totalUnopposed).toBe(22);
		expect(summary.totalRaces).toBe(211);
	});

	it('counts party breakdown correctly for MA 2026', () => {
		const ma = loadElectionData('massachusetts_2026.json');
		const map = new Map<string, ElectionData | null>([['MA', ma]]);
		const summary = calculateSummary(map);

		const totalByParty = Object.values(summary.countByParty).reduce((a, b) => a + b, 0);
		expect(totalByParty).toBe(22);
	});

	it('handles multiple states correctly', () => {
		const ma = loadElectionData('massachusetts_2026.json');
		const va = loadElectionData('virginia_2025.json');
		const map = new Map<string, ElectionData | null>([
			['MA', ma],
			['VA', va]
		]);
		const summary = calculateSummary(map);

		expect(summary.totalUnopposed).toBe(ma.total + va.total);
		expect(summary.totalRaces).toBe((ma.total_races || 0) + (va.total_races || 0));
	});

	it('handles null election data', () => {
		const ma = loadElectionData('massachusetts_2026.json');
		const map = new Map<string, ElectionData | null>([
			['MA', ma],
			['XX', null]
		]);
		const summary = calculateSummary(map);

		expect(summary.totalUnopposed).toBe(22);
	});
});
