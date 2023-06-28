import './assets/normalize.css'
import "carbon-components-svelte/css/white.css"
import './assets/markdown.css'
import 'highlight.js/styles/github.css';
import './assets/global.css'
// @ts-ignore
import App from './App.svelte'

const app = new App({
  target: document.getElementById('app'),
})

export default app
