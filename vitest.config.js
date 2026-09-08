import { defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        environment: 'jsdom',
        globals: true,
        include: ['tests/unit/**/*.test.js'],
        setupFiles: ['tests/unit/setup.js'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'html', 'json-summary'],
            // Full static/ tree so the report is honest: untested tab entry
            // files (option-chain.js, simulation.js, …) must show up as 0%
            // instead of silently disappearing from the summary.
            include: ['static/**/*.js'],
            reportsDirectory: 'coverage/js',
        },
    },
});
