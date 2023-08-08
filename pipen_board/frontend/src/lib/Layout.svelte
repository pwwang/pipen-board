<script>
    // Used by ../App.svelte
    import { onMount } from "svelte";
    import Tabs from "carbon-components-svelte/src/Tabs/Tabs.svelte";
    import Tab from "carbon-components-svelte/src/Tabs/Tab.svelte";
    import TabContent from "carbon-components-svelte/src/Tabs/TabContent.svelte";
    import Modal from "carbon-components-svelte/src/Modal/Modal.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import Loading from "carbon-components-svelte/src/Loading/Loading.svelte";
    import Settings from "carbon-icons-svelte/lib/Settings.svelte";
    import WatsonHealthStatusAcknowledge from "carbon-icons-svelte/lib/WatsonHealthStatusAcknowledge.svelte";
    import ContinueFilled from "carbon-icons-svelte/lib/ContinueFilled.svelte";
    import SkipBack from "carbon-icons-svelte/lib/SkipBack.svelte";
    import CheckmarkOutline from "carbon-icons-svelte/lib/CheckmarkOutline.svelte";
    import Warning from "carbon-icons-svelte/lib/Warning.svelte";
    import { storedGlobalChanged, presetConfig } from "./store";

    import { IS_DEV, getStatusPercentage, fetchAPI } from "./utils";
    import Header from "./Header.svelte";
    import Configuration from "./Configuration.svelte";
    import Run from "./Run.svelte";
    import { SECTION_PIPELINE_OPTS } from "./constants";

    export let configfile;
    export let histories;

    // 0: not run, show previous run data
    // 1: first run trial
    // 2: 2nd run trial
    let runStarted = 0;
    // If the pipeline is running, whether it is finished
    let finished = false;
    let config_data;
    let run_data;

    let loadingData = true;
    let error;

    let pipelineName = "Loading";
    let pipelineDesc = "Loading ...";
    // success, failure, running, init
    let statusPercent = [0, 0, 0, 100];

    let selectedTab = 0;

    $: if (runStarted) {
        statusPercent = [0, 0, 0, 100];
        selectedTab = 1;
    }

    const loadData = async () => {
        let data;
        try {
            data = await fetchAPI("/api/pipeline", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ configfile, preset: $presetConfig }),
            });
        } catch (e) {
            error = `<strong>Failed to fetch or parse data:</strong> <br /><br /><pre>${e}</pre>`;
        } finally {
            loadingData = false;
            presetConfig.set(undefined);
        }
        if (!error) {
            if (IS_DEV) {
                // @ts-ignore
                window.data = data;
            }

            runStarted = data.runStarted + 0;
            config_data = data.config;
            run_data = data.run;
            pipelineName = config_data[SECTION_PIPELINE_OPTS].name.value;
            pipelineDesc = config_data[SECTION_PIPELINE_OPTS].desc.value;
            statusPercent = getStatusPercentage(run_data);
        }
        storedGlobalChanged.set(false);
    };

    onMount(loadData);
</script>

<svelte:head>
<title>{pipelineName} :: PIPEN BOARD</title>
</svelte:head>

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
    <br />
    <Button
        kind="tertiary"
        size="small"
        on:click={() => {
            configfile = undefined;
        }}
        icon={SkipBack}
    >Back to History</Button>
</Modal>
{:else if loadingData}
<Loading
    class="pipen-cli-config-loading"
    style="--content: 'Loading pipeline data ...\A'"
    description="Loading pipeline data ..." />
{:else}
  <div class="body">
    <Header {pipelineName} {pipelineDesc} isRunning={runStarted && !finished} backToHistory bind:configfile />
    <div class="pipen-tabs">
        <Tabs style="border-bottom: 2px solid #e0e0e0" bind:selected={selectedTab}>
            <Tab><Settings />Configuration</Tab>
            <Tab
                class="run-tab {runStarted && (statusPercent[2] > 0 || !finished) ? 'running' : ''}"
                style="--n_succ: {statusPercent[0]}%; --n_fail: {statusPercent[1]}%; --n_run: {statusPercent[2]}%; --n_init: {statusPercent[3]}%"
            >
                {#if runStarted && finished === "error"}
                <Warning style="stroke: #ff001d" /><span class="runtab-title">Finished</span>
                {:else if runStarted && finished}
                <CheckmarkOutline /><span class="runtab-title">Finished</span>
                {:else if runStarted && !finished}
                <ContinueFilled /><span class="runtab-title">Running</span>
                {:else}
                <WatsonHealthStatusAcknowledge /><span class="runtab-title">Previous Run</span>
                {/if}
            </Tab>
            <svelte:fragment slot="content">
                <TabContent>
                    <Configuration
                        data={config_data}
                        {finished}
                        bind:runStarted
                        bind:histories
                        bind:configfile
                        bind:pipelineDesc />
                </TabContent>
                <TabContent>
                    {#key runStarted}
                        <Run data={run_data} name={pipelineName} bind:finished bind:statusPercent bind:runStarted />
                    {/key}
                </TabContent>
            </svelte:fragment>
        </Tabs>
    </div>
  </div>
{/if}

<style>
div.body {
    display: grid;
    grid-template-areas:
        "header"
        "content";
    grid-template-rows: auto 1fr;
    grid-template-columns: 1fr;
    height: 100vh;
}
div.pipen-tabs {
    grid-area: content;
    display: grid;
    grid-template-rows: auto 1fr;
    grid-template-columns: 1fr;
    /* https://stackoverflow.com/a/71024439/5088165 */
    min-height: 0;
}
div.pipen-tabs span.runtab-title {
    min-width: 5rem;
}
</style>
