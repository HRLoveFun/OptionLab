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
            include: [
                'static/api.js',
                'static/eventBus.js',
                'static/utils.js',
                'static/state/**/*.js',
            ],
            reportsDirectory: 'coverage/js',
        },
    },
});
