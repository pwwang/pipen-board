<script>
    import { onMount } from "svelte";
    import Loading from "carbon-components-svelte/src/Loading/Loading.svelte";
    import Modal from "carbon-components-svelte/src/Modal/Modal.svelte";

    import { IS_DEV } from "./lib/utils";
    import { storedConfigfile } from "./lib/store";
    import History from "./lib/History.svelte";
    import Layout from "./lib/Layout.svelte";
    import { fetchAPI} from "./lib/utils";

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
            fetched_history = await fetchAPI("/api/history");
        } catch (e) {
            error = e;
        } finally {
            fetching_history = false;
        }

        if (!error) {
            pipeline = fetched_history.pipeline;
            histories = fetched_history.histories;
            const stored = histories.find(h => h.configfile === $storedConfigfile && h.is_current);
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
            {#key configfile}
                <Layout bind:histories bind:configfile />
            {/key}
        {/if}
    {/if}
{/if}