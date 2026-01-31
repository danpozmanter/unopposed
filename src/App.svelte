<script lang="ts">
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import {
		STATE_NAMES,
		STATE_CODES,
		getFilename,
		getDefaultYear,
		type ElectionData,
		type Candidate,
		type Manifest
	} from '$lib/types';

	const baseUrl = import.meta.env.BASE_URL;

	let availableYears = $state<number[]>([]);
	let selectedYear = $state(getDefaultYear());
	let electionsByState = new SvelteMap<string, ElectionData | null>();
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
				const manifest: Manifest = await response.json();
				availableYears = manifest.years.sort((a, b) => b - a);
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

	const summary = $derived.by(() => {
		let totalUnopposed = 0;
		const countByParty: Record<string, number> = {};

		for (const electionData of electionsByState.values()) {
			if (electionData?.unopposed_candidates) {
				totalUnopposed += electionData.total || 0;
				for (const candidate of electionData.unopposed_candidates) {
					const { abbrev } = getPartyInfo(candidate.party);
					countByParty[abbrev] = (countByParty[abbrev] || 0) + 1;
				}
			}
		}

		return { totalUnopposed, countByParty };
	});

	$effect(() => {
		loadManifest();
	});

	$effect(() => {
		if (availableYears.length > 0) {
			loadElectionData(selectedYear);
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
			<div class="summary-card">
				<span class="summary-number">{summary.totalUnopposed}</span>
				<span class="summary-label">Unopposed Races</span>
			</div>
			<div class="summary-parties">
				{#each Object.entries(summary.countByParty).sort((a, b) => b[1] - a[1]) as [partyAbbrev, count] (partyAbbrev)}
					<div class="party-stat">
						<span class="party-badge party-{partyAbbrev.toLowerCase()}">{partyAbbrev}</span>
						<span class="party-count">{count}</span>
					</div>
				{/each}
			</div>
		</section>

		<div class="party-key">
			<span><span class="party-badge party-d">D</span> Democrat</span>
			<span><span class="party-badge party-r">R</span> Republican</span>
			<span><span class="party-badge party-l">L</span> Libertarian</span>
			<span><span class="party-badge party-g">G</span> Green</span>
			<span><span class="party-badge party-i">I</span> Independent</span>
			<span><span class="party-badge party-o">O</span> Other</span>
		</div>

		<section class="states-grid">
			{#each STATE_CODES.filter((stateCode) => {
				const electionData = electionsByState.get(stateCode);
				return electionData && electionData.total > 0;
			}) as stateCode (stateCode)}
				{@const electionData = electionsByState.get(stateCode)}
				<article class="state-card" class:expanded={expandedStates.has(stateCode)}>
					<button class="state-header" onclick={() => toggleStateExpansion(stateCode)}>
						<div class="state-info">
							<span class="state-code">{stateCode}</span>
							<span class="state-name">{STATE_NAMES[stateCode]}</span>
						</div>
						<div class="state-count">
							<span class="count-badge">{electionData?.total || 0}</span>
						</div>
					</button>

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
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.summary-card {
		display: flex;
		flex-direction: column;
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
	.party-badge.party-o,
	.party-badge.party-u {
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
		padding: 1rem;
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

	.count-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2.5rem;
		height: 2rem;
		padding: 0 0.5rem;
		background: #1a1a1a;
		color: white;
		border-radius: 1rem;
		font-weight: 600;
		font-size: 0.9rem;
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
	}
</style>
