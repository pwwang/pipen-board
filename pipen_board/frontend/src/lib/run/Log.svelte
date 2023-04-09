<script>
    // Used by ../Run.svelte
	import { beforeUpdate, afterUpdate } from 'svelte';
    import CodeSnippet from "carbon-components-svelte/src/CodeSnippet/CodeSnippet.svelte";
    export let log;

    let container;
	let autoscroll;

	beforeUpdate(() => {
		autoscroll = container && (container.offsetHeight + container.scrollTop) > (container.scrollHeight - 20);
	});

	afterUpdate(() => {
		if (autoscroll) container.scrollTo(0, container.scrollHeight);
	});

</script>

<div class="run-log" bind:this={container}>
    <CodeSnippet
        type="multi"
        expanded
        showMoreLess={false}
        code={log ||  "Starting the pipeline..."}
        class="run-log__code"
    />
</div>

<style>
    div.run-log {
        height: 100%;
        overflow: auto;
    }
</style>
