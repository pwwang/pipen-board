<script>
    import Tabs from "carbon-components-svelte/src/Tabs/Tabs.svelte";
    import Tab from "carbon-components-svelte/src/Tabs/Tab.svelte";
    import TabContent from "carbon-components-svelte/src/Tabs/TabContent.svelte";
    import Settings from "carbon-icons-svelte/lib/Settings.svelte";
    import WatsonHealthStatusAcknowledge from "carbon-icons-svelte/lib/WatsonHealthStatusAcknowledge.svelte";
    import ContinueFilled from "carbon-icons-svelte/lib/ContinueFilled.svelte";

    import Header from "./Header.svelte";
    import Configuration from "./Configuration.svelte";
    import PreviousRun from "./PreviousRun.svelte";

    export let configfile;
    // start fetching data?
    export let start;
    export let histories;

    let pipelineName = "Loading";
    let pipelineDesc = "Loading ...";

    let running = false;
    let selectedTab = 0;

    // success, failure, unrun
    let prev_success = [0, 0, 100];

  </script>

  <svelte:head>
    <title>{pipelineName} :: PIPEN BOARD</title>
  </svelte:head>

  <div class="body">
    <Header {pipelineName} {pipelineDesc} backToHistory bind:configfile {histories} />
    <div class="pipen-tabs">
        <Tabs style="border-bottom: 2px solid #e0e0e0" bind:selected={selectedTab}>
            <Tab><Settings />Configuration</Tab>
            <Tab
                class="prev-run-tab"
                style="--n_succ: {prev_success[0]}%; --n_fail: {prev_success[1]}%; --n_unrun: {prev_success[2]}%"
            ><WatsonHealthStatusAcknowledge />Previous Run</Tab>
            {#if running}
                <Tab><ContinueFilled />Running</Tab>
            {/if}
            <svelte:fragment slot="content">
                <TabContent>
                    <Configuration {start} bind:histories bind:configfile bind:pipelineName bind:pipelineDesc />
                </TabContent>
                <TabContent>
                    <PreviousRun bind:prev_success selected={selectedTab === 1} {configfile} />
                </TabContent>
                {#if running}
                    <TabContent>
                        Running
                    </TabContent>
                {/if}
            </svelte:fragment>
        </Tabs>
    </div>
  </div>

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
    }
  </style>
