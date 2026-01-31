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

	const base = import.meta.env.BASE_URL.replace(/\/$/, '');

	let years = $state<number[]>([]);
	let selectedYear = $state(getDefaultYear());
	let stateData = new SvelteMap<string, ElectionData | null>();
	let loading = $state(true);
	let expandedStates = new SvelteSet<string>();

	const officeOrder = ['US Senate', 'US House', 'Governor', 'State Senate', 'State House'];

	async function loadManifest() {
		try {
			const response = await fetch(`${base}/election_data/manifest.json`);
			if (response.ok) {
				const manifest: Manifest = await response.json();
				years = manifest.years.sort((a, b) => b - a);
				const currentYear = getDefaultYear();
				if (years.includes(currentYear)) {
					selectedYear = currentYear;
				} else if (years.length > 0) {
					selectedYear = years[years.length - 1];
				}
			}
		} catch {
			years = [getDefaultYear()];
		}
	}

	async function loadData(year: number) {
		loading = true;
		const newData = new SvelteMap<string, ElectionData | null>();

		const statePromises = STATE_CODES.map(async (code) => {
			const filename = getFilename(code);
			try {
				const response = await fetch(`${base}/election_data/${filename}_${year}.json`);
				if (response.ok) {
					const data = await response.json();
					newData.set(code, data);
				} else {
					newData.set(code, null);
				}
			} catch {
				newData.set(code, null);
			}
		});

		await Promise.all(statePromises);

		stateData = newData;
		loading = false;
	}

	function getPartyClass(party: string): string {
		const p = party.toLowerCase();
		if (p.includes('democrat')) return 'party-d';
		if (p.includes('republican')) return 'party-r';
		if (p.includes('libertarian')) return 'party-l';
		if (p.includes('green')) return 'party-g';
		if (p.includes('independent')) return 'party-i';
		return 'party-o';
	}

	function getPartyAbbreviation(party: string): string {
		const p = party.toLowerCase();
		if (p.includes('democrat')) return 'D';
		if (p.includes('republican')) return 'R';
		if (p.includes('libertarian')) return 'L';
		if (p.includes('green')) return 'G';
		if (p.includes('independent')) return 'I';
		if (p.includes('unknown') || p === 'unknown') return 'U';
		return 'O';
	}

	function groupByOffice(candidates: Candidate[]): Map<string, Candidate[]> {
		// eslint-disable-next-line svelte/prefer-svelte-reactivity -- pure utility function, not reactive state
		const grouped = new Map<string, Candidate[]>();
		for (const c of candidates) {
			if (!grouped.has(c.office)) {
				grouped.set(c.office, []);
			}
			grouped.get(c.office)!.push(c);
		}
		return new Map(
			[...grouped.entries()].sort(
				(a, b) => officeOrder.indexOf(a[0]) - officeOrder.indexOf(b[0])
			)
		);
	}

	function toggleState(code: string) {
		if (expandedStates.has(code)) {
			expandedStates.delete(code);
		} else {
			expandedStates.add(code);
		}
	}

	function formatTimestamp(iso: string): string {
		const date = new Date(iso);
		return date.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getSummary(): { total: number; byParty: Record<string, number> } {
		let total = 0;
		const byParty: Record<string, number> = {};

		for (const data of stateData.values()) {
			if (data?.unopposed_candidates) {
				total += data.total || 0;
				for (const c of data.unopposed_candidates) {
					const abbrev = getPartyAbbreviation(c.party);
					byParty[abbrev] = (byParty[abbrev] || 0) + 1;
				}
			}
		}

		return { total, byParty };
	}

	$effect(() => {
		loadManifest();
	});

	$effect(() => {
		if (years.length > 0) {
			loadData(selectedYear);
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
		{#each years as year (year)}
			<button
				class="year-btn"
				class:active={selectedYear === year}
				onclick={() => (selectedYear = year)}
			>
				{year}
			</button>
		{/each}
	</nav>

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
			<p>Loading election data...</p>
		</div>
	{:else}
		{@const summary = getSummary()}
		<section class="summary">
			<div class="summary-card">
				<span class="summary-number">{summary.total}</span>
				<span class="summary-label">Unopposed Races</span>
			</div>
			<div class="summary-parties">
				{#each Object.entries(summary.byParty).sort((a, b) => b[1] - a[1]) as [party, count] (party)}
					<div class="party-stat">
						<span class="party-badge party-{party.toLowerCase()}">{party}</span>
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
			{#each STATE_CODES.filter(code => {
				const d = stateData.get(code);
				return d && d.total > 0;
			}) as code (code)}
				{@const data = stateData.get(code)}
				<article class="state-card" class:expanded={expandedStates.has(code)}>
					<button class="state-header" onclick={() => toggleState(code)}>
						<div class="state-info">
							<span class="state-code">{code}</span>
							<span class="state-name">{STATE_NAMES[code]}</span>
						</div>
						<div class="state-count">
							<span class="count-badge">{data?.total || 0}</span>
						</div>
					</button>

					{#if expandedStates.has(code) && data?.unopposed_candidates && data.total > 0}
						{@const grouped = groupByOffice(data.unopposed_candidates)}
						<div class="state-details">
							{#if data.scraped_at}
								<p class="scraped-at">As of {formatTimestamp(data.scraped_at)}</p>
							{/if}
							{#each [...grouped.entries()] as [office, candidates] (office)}
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
											{#each candidates as c (c.candidate + c.district)}
												<tr>
													<td class="district">{c.district}</td>
													<td class="candidate-name">{c.candidate}</td>
													<td>
														<span class="party-pill {getPartyClass(c.party)}">
															{getPartyAbbreviation(c.party)}
														</span>
													</td>
													<td class="unopposed-in">{c.unopposed_in}</td>
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
