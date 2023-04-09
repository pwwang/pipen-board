<script>
    import { onMount } from "svelte";
    import Loading from "carbon-components-svelte/src/Loading/Loading.svelte";
    import Modal from "carbon-components-svelte/src/Modal/Modal.svelte";

    import { IS_DEV } from "./lib/utils";
    import { storedConfigfile } from "./lib/store";
    import History from "./lib/History.svelte";
    import Layout from "./lib/Layout.svelte";

    // example.py:ExamplePipeline
    let pipeline;
    // [{"name": "ExamplePipeline", "configfile": "/path/to/config", "time": "2021-01-01 00:00:00" }]
    let histories = [];
    let configfile;
    let fetching_history = true;
    let error;

    const beforeUnload = function (event) {
        if (!IS_DEV) {
            event.preventDefault();
            event.returnValue = "";
        }
    };

    onMount(async () => {
        let fetched_history;
        try {
            const fetched = await fetch("/api/history");
            if (!fetched.ok)
                throw new Error(`${fetched.status} ${fetched.statusText}`);
            fetched_history = await fetched.json();
        } catch (e) {
            error = `<strong>Failed to fetch or parse history data:</strong> <br /><br /><pre>${e.stack}</pre>`;
        } finally {
            fetching_history = false;
        }

        if (!error) {
            pipeline = fetched_history.pipeline;
            histories = fetched_history.histories;
            const stored = histories.find(h => h.configfile === $storedConfigfile);
            if (stored) {
                configfile = stored.configfile;
            }
        }
    })
</script>

<svelte:head>
  <title>PIPEN BOARD</title>
</svelte:head>

<svelte:window on:beforeunload={beforeUnload} />


{#if error}
<Modal
    class="model-error"
    passiveModal
    danger
    open={true}
    preventCloseOnClickOutside={true}
    modalHeading="Error"
    on:close={() => {}}
>
    {@html error}
</Modal>
{:else}
    {#if fetching_history}
    <Loading
        class="pipen-cli-config-loading"
        style="--content: 'Fetching history ...'"
        description="Fetching history ..." />

    {:else}
        {#if histories.length > 0 && configfile === undefined}
        <History {pipeline} bind:histories bind:configfile />
        {:else}
        <Layout bind:histories bind:configfile />
        {/if}
    {/if}
{/if}