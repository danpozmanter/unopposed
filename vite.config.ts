import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

export default defineConfig({
	plugins: [
		{
			name: 'serve-election-data',
			configureServer(server) {
				server.middlewares.use('/election_data', (req, res, next) => {
					const filePath = join(process.cwd(), 'election_data', req.url || '');
					if (existsSync(filePath)) {
						res.setHeader('Content-Type', 'application/json');
						res.end(readFileSync(filePath));
					} else {
						next();
					}
				});
			}
		},
		svelte()
	],
	resolve: {
		alias: {
			$lib: '/src/lib'
		}
	},
	build: {
		outDir: 'dist'
	}
});
