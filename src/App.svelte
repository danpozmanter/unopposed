<script lang="ts">
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import {
		STATE_NAMES,
		STATE_CODES,
		getFilename,
		getDefaultYear,
		type ElectionData,
		type Candidate,
		type Manifest,
		type NationwideStats
	} from '$lib/types';

	const baseUrl = import.meta.env.BASE_URL;

	let manifest = $state<Manifest | null>(null);
	let availableYears = $state<number[]>([]);
	let selectedYear = $state(getDefaultYear());
	let electionsByState = new SvelteMap<string, ElectionData | null>();
	let nationwideStats = $state<NationwideStats | null>(null);
	let isLoading = $state(true);
	let expandedStates = new SvelteSet<string>();

	const OFFICE_PRIORITY = ['US Senate', 'US House', 'Governor', 'State Senate', 'State House'] as const;

	const PARTY_INFO: Record<string, { abbrev: string; class: string }> = {
		democrat: { abbrev: 'D', class: 'party-d' },
		republican: { abbrev: 'R', class: 'party-r' },
		libertarian: { abbrev: 'L', class: 'party-l' },
		green: { abbrev: 'G', class: 'party-g' },
		independent: { abbrev: 'I', class: 'party-i' },
		unknown: { abbrev: 'U', class: 'party-o' }
	};

	function getPartyInfo(party: string): { abbrev: string; class: string } {
		const partyLower = party.toLowerCase();
		for (const [key, info] of Object.entries(PARTY_INFO)) {
			if (partyLower.includes(key)) return info;
		}
		return { abbrev: 'O', class: 'party-o' };
	}

	async function loadManifest() {
		try {
			const response = await fetch(`${baseUrl}election_data/manifest.json`);
			if (response.ok) {
				manifest = await response.json();
				availableYears = manifest!.years.sort((a, b) => b - a);
				const currentYear = getDefaultYear();
				if (availableYears.includes(currentYear)) {
					selectedYear = currentYear;
				} else if (availableYears.length > 0) {
					selectedYear = availableYears[0];
				}
			} else {
				availableYears = [getDefaultYear()];
			}
		} catch {
			availableYears = [getDefaultYear()];
		}
	}

	async function loadNationwideStats(year: number) {
		try {
			const response = await fetch(`${baseUrl}election_data/nationwide_${year}.json`);
			if (response.ok) {
				nationwideStats = await response.json();
			} else {
				nationwideStats = null;
			}
		} catch {
			nationwideStats = null;
		}
	}

	async function loadElectionData(year: number) {
		isLoading = true;
		electionsByState.clear();

		const fetchPromises = STATE_CODES.map(async (stateCode) => {
			const filename = getFilename(stateCode);
			try {
				const response = await fetch(`${baseUrl}election_data/${filename}_${year}.json`);
				if (response.ok) {
					const data = await response.json();
					electionsByState.set(stateCode, data);
				} else {
					electionsByState.set(stateCode, null);
				}
			} catch {
				electionsByState.set(stateCode, null);
			}
		});

		await Promise.all(fetchPromises);
		isLoading = false;
	}

	function groupCandidatesByOffice(candidates: Candidate[]): Map<string, Candidate[]> {
		// eslint-disable-next-line svelte/prefer-svelte-reactivity -- pure utility, not reactive state
		const grouped = new Map<string, Candidate[]>();
		for (const candidate of candidates) {
			if (!grouped.has(candidate.office)) {
				grouped.set(candidate.office, []);
			}
			grouped.get(candidate.office)!.push(candidate);
		}
		return new Map(
			[...grouped.entries()].sort(
				(a, b) => OFFICE_PRIORITY.indexOf(a[0] as typeof OFFICE_PRIORITY[number]) - OFFICE_PRIORITY.indexOf(b[0] as typeof OFFICE_PRIORITY[number])
			)
		);
	}

	function toggleStateExpansion(stateCode: string) {
		if (expandedStates.has(stateCode)) {
			expandedStates.delete(stateCode);
		} else {
			expandedStates.add(stateCode);
		}
	}

	function formatDate(isoString: string): string {
		return new Date(isoString).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function computeStateStats(data: ElectionData) {
		const candidates = data.unopposed_candidates || [];
		const totalRaces = data.total_races || 0;
		const totalRacesByParty = data.total_races_by_party || {};

		// eslint-disable-next-line svelte/prefer-svelte-reactivity -- pure utility, not reactive state
		const generalRaces = new Set<string>();
		const generalByParty: Record<string, number> = {};
		const primaryRacesByParty: Record<string, Set<string>> = {};
		const primaryUnopposedByParty: Record<string, number> = {};

		for (const c of candidates) {
			const raceKey = `${c.office}:${c.district}`;
			if (c.unopposed_in.includes('General')) {
				generalRaces.add(raceKey);
				const { abbrev } = getPartyInfo(c.party);
				generalByParty[abbrev] = (generalByParty[abbrev] || 0) + 1;
			}
			if (c.unopposed_in.includes('Primary')) {
				const { abbrev } = getPartyInfo(c.party);
				if (!primaryRacesByParty[abbrev]) primaryRacesByParty[abbrev] = new Set();
				primaryRacesByParty[abbrev].add(raceKey);
				primaryUnopposedByParty[abbrev] = (primaryUnopposedByParty[abbrev] || 0) + 1;
			}
		}

		const primaryTotalByParty: Record<string, number> = {};
		for (const [party, count] of Object.entries(totalRacesByParty)) {
			const { abbrev } = getPartyInfo(party);
			primaryTotalByParty[abbrev] = (primaryTotalByParty[abbrev] || 0) + count;
		}

		const primaryTotalRaces = Object.values(primaryTotalByParty).reduce((sum, n) => sum + n, 0);

		return {
			general: {
				totalUnopposed: generalRaces.size,
				totalRaces,
				byParty: generalByParty
			},
			primary: {
				totalUnopposed: Object.values(primaryRacesByParty).reduce((sum, s) => sum + s.size, 0),
				totalRaces: primaryTotalRaces,
				byParty: primaryUnopposedByParty,
				totalByParty: primaryTotalByParty
			}
		};
	}

	const generalSummary = $derived.by(() => {
		const stats = nationwideStats;
		if (!stats?.general) return null;

		const unopposedByPartyAbbrev: Record<string, number> = {};
		for (const [party, count] of Object.entries(stats.general.unopposed_by_party)) {
			const { abbrev } = getPartyInfo(party);
			unopposedByPartyAbbrev[abbrev] = (unopposedByPartyAbbrev[abbrev] || 0) + count;
		}

		return {
			totalUnopposed: stats.general.total_unopposed,
			totalRaces: stats.general.total_races,
			unopposedByParty: unopposedByPartyAbbrev
		};
	});

	const primarySummary = $derived.by(() => {
		const stats = nationwideStats;
		if (!stats?.primary) return null;

		const unopposedByPartyAbbrev: Record<string, number> = {};
		const totalByPartyAbbrev: Record<string, number> = {};

		for (const [party, count] of Object.entries(stats.primary.unopposed_by_party)) {
			const { abbrev } = getPartyInfo(party);
			unopposedByPartyAbbrev[abbrev] = (unopposedByPartyAbbrev[abbrev] || 0) + count;
		}

		for (const [party, count] of Object.entries(stats.primary.total_races_by_party)) {
			const { abbrev } = getPartyInfo(party);
			totalByPartyAbbrev[abbrev] = (totalByPartyAbbrev[abbrev] || 0) + count;
		}

		const totalRaces = Object.values(totalByPartyAbbrev).reduce((sum, n) => sum + n, 0);

		return {
			totalUnopposed: stats.primary.total_unopposed,
			totalRaces,
			unopposedByParty: unopposedByPartyAbbrev,
			totalByParty: totalByPartyAbbrev
		};
	});

	$effect(() => {
		loadManifest();
	});

	$effect(() => {
		if (availableYears.length > 0) {
			loadElectionData(selectedYear);
			loadNationwideStats(selectedYear);
		}
	});

	$effect(() => {
		document.title = `Unopposed | ${selectedYear} Elections`;
	});
</script>

<div class="container">
	<header>
		<h1>Unopposed</h1>
		<p class="subtitle">Tracking elections where voters have no choice</p>
	</header>

	<nav class="year-selector">
		{#each availableYears as year (year)}
			<button
				class="year-btn"
				class:active={selectedYear === year}
				onclick={() => (selectedYear = year)}
			>
				{year}
			</button>
		{/each}
	</nav>

	{#if isLoading}
		<div class="loading">
			<div class="spinner"></div>
			<p>Loading election data...</p>
		</div>
	{:else}
		<section class="summary">
			{#if generalSummary}
				<div class="summary-section">
					<h2 class="summary-title">General Election</h2>
					<div class="summary-card">
						<span class="summary-number">{generalSummary.totalUnopposed}<span class="summary-total">/{generalSummary.totalRaces}</span></span>
						<span class="summary-label">Unopposed Races{#if generalSummary.totalRaces > 0} ({(generalSummary.totalUnopposed / generalSummary.totalRaces * 100).toFixed(1)}%){/if}</span>
					</div>
					<div class="summary-parties">
						{#each Object.entries(generalSummary.unopposedByParty).sort((a, b) => b[1] - a[1]) as [partyAbbrev, count] (partyAbbrev)}
							<div class="party-stat">
								<span class="party-badge party-{partyAbbrev.toLowerCase()}">{partyAbbrev}</span>
								<span class="party-count">{count}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
			{#if primarySummary}
				<div class="summary-section">
					<h2 class="summary-title">Primary Elections</h2>
					<div class="summary-card">
						<span class="summary-number">{primarySummary.totalUnopposed}<span class="summary-total">/{primarySummary.totalRaces}</span></span>
						<span class="summary-label">Unopposed Primaries{#if primarySummary.totalRaces > 0} ({(primarySummary.totalUnopposed / primarySummary.totalRaces * 100).toFixed(1)}%){/if}</span>
					</div>
					<div class="summary-parties">
						{#each Object.entries(primarySummary.unopposedByParty).sort((a, b) => b[1] - a[1]) as [partyAbbrev, count] (partyAbbrev)}
							{@const totalForParty = primarySummary.totalByParty[partyAbbrev] || 0}
							<div class="party-stat">
								<span class="party-badge party-{partyAbbrev.toLowerCase()}">{partyAbbrev}</span>
								<span class="party-count">{count}{#if totalForParty > 0}<span class="party-total">/{totalForParty}</span>{/if}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</section>

		<div class="party-key">
			<span><span class="party-badge party-d">D</span> Democrat</span>
			<span><span class="party-badge party-r">R</span> Republican</span>
			<span><span class="party-badge party-l">L</span> Libertarian</span>
			<span><span class="party-badge party-g">G</span> Green</span>
			<span><span class="party-badge party-i">I</span> Independent</span>
			<span><span class="party-badge party-u">U</span> Unknown</span>
			<span><span class="party-badge party-o">O</span> Other</span>
		</div>

		<section class="states-grid">
			{#each STATE_CODES.filter((stateCode) => {
				const electionData = electionsByState.get(stateCode);
				return electionData && electionData.total_races > 0;
			}) as stateCode (stateCode)}
				{@const electionData = electionsByState.get(stateCode)}
				{@const stateStats = electionData ? computeStateStats(electionData) : null}
				<article class="state-card" class:expanded={expandedStates.has(stateCode)}>
					<button class="state-header" onclick={() => toggleStateExpansion(stateCode)}>
						<div class="state-info">
							<span class="state-code">{stateCode}</span>
							<span class="state-name">{STATE_NAMES[stateCode]}</span>
						</div>
					</button>
					{#if stateStats}
						<div class="state-stats">
							<div class="state-stat-section">
								<span class="state-stat-label">General</span>
								<span class="state-stat-value">{stateStats.general.totalUnopposed}<span class="state-stat-total">/{stateStats.general.totalRaces}</span></span>
								<div class="state-stat-parties">
									{#each Object.entries(stateStats.general.byParty).sort((a, b) => b[1] - a[1]) as [abbrev, count] (abbrev)}
										<span class="party-mini party-{abbrev.toLowerCase()}">{abbrev}:{count}</span>
									{/each}
								</div>
							</div>
							<div class="state-stat-section">
								<span class="state-stat-label">Primary</span>
								<span class="state-stat-value">{stateStats.primary.totalUnopposed}<span class="state-stat-total">/{stateStats.primary.totalRaces}</span></span>
								<div class="state-stat-parties">
									{#each Object.entries(stateStats.primary.byParty).sort((a, b) => b[1] - a[1]) as [abbrev, count] (abbrev)}
										{@const total = stateStats.primary.totalByParty[abbrev] || 0}
										<span class="party-mini party-{abbrev.toLowerCase()}">{abbrev}:{count}{#if total > 0}<span class="party-mini-total">/{total}</span>{/if}</span>
									{/each}
								</div>
							</div>
						</div>
					{/if}

					{#if expandedStates.has(stateCode) && electionData?.unopposed_candidates && electionData.total > 0}
						{@const candidatesByOffice = groupCandidatesByOffice(electionData.unopposed_candidates)}
						<div class="state-details">
							{#if electionData.scraped_at}
								<p class="scraped-at">As of {formatDate(electionData.scraped_at)}</p>
							{/if}
							{#each [...candidatesByOffice.entries()] as [office, candidates] (office)}
								<div class="office-group">
									<h3 class="office-title">{office}</h3>
									<table class="candidates-table">
										<thead>
											<tr>
												<th>District</th>
												<th>Candidate</th>
												<th>Party</th>
												<th>Unopposed In</th>
											</tr>
										</thead>
										<tbody>
											{#each candidates as candidate (candidate.candidate + candidate.district)}
												{@const partyInfo = getPartyInfo(candidate.party)}
												<tr>
													<td class="district">{candidate.district}</td>
													<td class="candidate-name">{candidate.candidate}</td>
													<td>
														<span class="party-pill {partyInfo.class}">
															{partyInfo.abbrev}
														</span>
													</td>
													<td class="unopposed-in">{candidate.unopposed_in}</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							{/each}
						</div>
					{/if}
				</article>
			{:else}
				<p class="no-data-message">No election data available for {selectedYear}.</p>
			{/each}
		</section>
	{/if}

	<footer>
		<p>Data sourced from <a href="https://ballotpedia.org" target="_blank" rel="noopener">Ballotpedia</a></p>
		<p class="disclaimer">Data may not be complete or fully accurate. Verify with official sources.</p>
		<p class="source-link">
			<a href="https://github.com/danpozmanter/unopposed" target="_blank" rel="noopener">
				<svg class="github-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
					<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
				</svg>
				Source Code
			</a>
		</p>
	</footer>
</div>

<style>
	:global(*, *::before, *::after) {
		box-sizing: border-box;
	}

	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
			sans-serif;
		background: #f8f9fa;
		color: #1a1a1a;
		line-height: 1.5;
	}

	.container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem 1rem;
	}

	header {
		text-align: center;
		margin-bottom: 2rem;
	}

	h1 {
		font-size: 2.5rem;
		font-weight: 700;
		margin: 0 0 0.5rem;
		letter-spacing: -0.02em;
	}

	.subtitle {
		color: #666;
		font-size: 1.1rem;
		margin: 0;
	}

	.year-selector {
		display: flex;
		justify-content: center;
		gap: 0.5rem;
		margin-bottom: 2rem;
	}

	.year-btn {
		padding: 0.75rem 1.5rem;
		border: 2px solid #e0e0e0;
		background: white;
		border-radius: 8px;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.year-btn:hover {
		border-color: #333;
	}

	.year-btn.active {
		background: #1a1a1a;
		color: white;
		border-color: #1a1a1a;
	}

	.loading {
		text-align: center;
		padding: 4rem 0;
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 3px solid #e0e0e0;
		border-top-color: #1a1a1a;
		border-radius: 50%;
		margin: 0 auto 1rem;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.summary {
		background: white;
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		display: flex;
		flex-wrap: wrap;
		gap: 2rem;
	}

	.summary-section {
		flex: 1;
		min-width: 280px;
	}

	.summary-title {
		font-size: 0.85rem;
		font-weight: 600;
		color: #666;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 0.75rem;
	}

	.summary-card {
		display: flex;
		flex-direction: column;
		margin-bottom: 0.75rem;
	}

	.summary-number {
		font-size: 3rem;
		font-weight: 700;
		line-height: 1;
	}

	.summary-label {
		color: #666;
		font-size: 0.9rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.summary-total {
		font-size: 1.5rem;
		font-weight: 400;
		color: #999;
	}

	.party-total {
		font-size: 0.9rem;
		font-weight: 400;
		color: #999;
	}

	.summary-parties {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.party-stat {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.party-badge {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 600;
		font-size: 0.8rem;
		color: white;
		background: #6b7280;
	}

	.party-badge.party-d {
		background: #2563eb;
	}
	.party-badge.party-r {
		background: #dc2626;
	}
	.party-badge.party-l {
		background: #f59e0b;
	}
	.party-badge.party-g {
		background: #16a34a;
	}
	.party-badge.party-i {
		background: #f0f0f0;
		color: #1a1a1a;
	}
	.party-badge.party-u {
		background: #7c3aed;
	}
	.party-badge.party-o {
		background: #6b7280;
	}

	.party-key {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		margin-bottom: 2rem;
		font-size: 0.85rem;
		color: #666;
	}

	.party-key > span {
		display: flex;
		align-items: center;
		gap: 0.35rem;
	}

	.party-key .party-badge {
		width: 20px;
		height: 20px;
		font-size: 0.7rem;
	}


	.party-count {
		font-weight: 600;
		font-size: 1.25rem;
	}

	.states-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1rem;
	}

	.state-card {
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
		transition: box-shadow 0.15s ease;
	}

	.state-card:hover {
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
	}

	.state-card.expanded {
		grid-column: 1 / -1;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
	}

	.state-header {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 1rem 0.5rem;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
	}

	.state-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.state-code {
		font-weight: 700;
		font-size: 1.1rem;
		color: #333;
		width: 2rem;
	}

	.state-name {
		color: #666;
	}

	.state-stats {
		display: flex;
		gap: 1.5rem;
		padding: 0 1rem 1rem;
	}

	.state-stat-section {
		flex: 1;
	}

	.state-stat-label {
		display: block;
		font-size: 0.7rem;
		font-weight: 600;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.25rem;
	}

	.state-stat-value {
		font-size: 1.25rem;
		font-weight: 700;
	}

	.state-stat-total {
		font-size: 0.9rem;
		font-weight: 400;
		color: #999;
	}

	.state-stat-parties {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin-top: 0.35rem;
	}

	.party-mini {
		font-size: 0.75rem;
		font-weight: 600;
		padding: 0.15rem 0.35rem;
		border-radius: 3px;
		background: #f0f0f0;
	}

	.party-mini.party-d { background: #dbeafe; color: #1e40af; }
	.party-mini.party-r { background: #fee2e2; color: #991b1b; }
	.party-mini.party-l { background: #fef3c7; color: #92400e; }
	.party-mini.party-g { background: #dcfce7; color: #166534; }
	.party-mini.party-i { background: #f3f4f6; color: #374151; }
	.party-mini.party-u { background: #ede9fe; color: #5b21b6; }
	.party-mini.party-o { background: #e5e7eb; color: #4b5563; }

	.party-mini-total {
		font-weight: 400;
		opacity: 0.7;
	}

	.no-data-message {
		grid-column: 1 / -1;
		text-align: center;
		color: #666;
		padding: 2rem;
	}

	.state-details {
		padding: 1rem 1.5rem 1.5rem;
		border-top: 1px solid #f0f0f0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
		gap: 1.5rem;
	}

	.scraped-at {
		grid-column: 1 / -1;
		margin: 0 0 0.5rem;
		font-size: 0.85rem;
		color: #888;
	}

	.office-group {
		margin: 0;
	}

	.office-title {
		font-size: 0.85rem;
		font-weight: 600;
		color: #666;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 0.5rem;
	}

	.candidates-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}

	.candidates-table th,
	.candidates-table td {
		padding: 0.5rem;
		text-align: left;
		border-bottom: 1px solid #f0f0f0;
	}

	.candidates-table th {
		font-weight: 500;
		color: #888;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.candidates-table tbody tr:last-child td {
		border-bottom: none;
	}

	.district {
		color: #666;
		font-size: 0.85rem;
	}

	.candidate-name {
		font-weight: 500;
	}

	.party-pill {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		font-weight: 600;
		font-size: 0.75rem;
		color: white;
		background: #6b7280;
	}

	.party-pill.party-d {
		background: #2563eb;
	}
	.party-pill.party-r {
		background: #dc2626;
	}
	.party-pill.party-l {
		background: #f59e0b;
	}
	.party-pill.party-g {
		background: #16a34a;
	}
	.party-pill.party-i {
		background: #f0f0f0;
		color: #1a1a1a;
	}
	.party-pill.party-o,
	.party-pill.party-u {
		background: #6b7280;
	}

	.unopposed-in {
		color: #666;
		font-size: 0.85rem;
	}

	footer {
		text-align: center;
		margin-top: 3rem;
		padding-top: 2rem;
		border-top: 1px solid #e0e0e0;
		color: #666;
	}

	footer a {
		color: #2563eb;
		text-decoration: none;
	}

	footer a:hover {
		text-decoration: underline;
	}

	.disclaimer {
		font-size: 0.85rem;
		color: #999;
	}

	.source-link {
		margin-top: 1rem;
	}

	.source-link a {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		color: #666;
		text-decoration: none;
		font-size: 0.9rem;
	}

	.source-link a:hover {
		color: #333;
	}

	.github-icon {
		width: 1rem;
		height: 1rem;
	}

	@media (max-width: 640px) {
		h1 {
			font-size: 1.75rem;
		}

		.summary {
			flex-direction: column;
			align-items: flex-start;
		}

		.year-selector {
			flex-wrap: wrap;
		}

		.year-btn {
			padding: 0.5rem 1rem;
		}

		.state-details {
			grid-template-columns: 1fr;
			padding: 1rem;
		}

		.candidates-table {
			display: block;
			overflow-x: auto;
		}
	}
</style>
