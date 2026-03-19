import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'fs'
import { execSync } from 'child_process'

const packageJson = JSON.parse(readFileSync('./package.json', 'utf-8'))

let submoduleVersion = 'Not inited'
try {
    submoduleVersion = execSync('git rev-parse --short HEAD', { cwd: '../libs/PCIETopoPainter' }).toString().trim()
} catch (e) {
    console.warn('Could not get submodule version', e)
}

// https://vite.dev/config/
export default defineConfig({
    plugins: [vue()],
    define: {
        __APP_VERSION__: JSON.stringify(packageJson.version),
        __SUBMODULE_VERSION__: JSON.stringify(submoduleVersion),
    },
})
