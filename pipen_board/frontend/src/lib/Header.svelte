<script>
    import { onMount } from "svelte";
    import Dashboard from "carbon-icons-svelte/lib/Dashboard.svelte";
    import DirectionLoopLeftFilled from "carbon-icons-svelte/lib/DirectionLoopLeftFilled.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import { fetchAPI } from "./utils";
    import { storedConfigfile } from "./store";

    export let pipelineName;
    export let pipelineDesc = undefined;
    export let backToHistory = false;
    export let configfile = undefined;
    export let histories;
    export let isRunning = false;

    let version = "0.0.0";

    const loadVersion = async function() {
        try {
            version = await fetchAPI("/api/version", {}, "text");
        } catch (e) {
            version = '<font style="color:red">Error</font>';
        }
    };

    onMount(loadVersion);
</script>

<header>
    <div class="header-left">
        <div class="wizard-desc">
            <Dashboard /> <a href="https://github.com/pwwang/pipen-board" target="_blank">PIPEN BOARD</a> <em>v{@html version}</em>
        </div>
        <h1>{pipelineName}</h1>
        <div>{pipelineDesc ? pipelineDesc : ""}</div>
    </div>
    <div class="header-right">
        {#if backToHistory}
            <Button
                on:click={() => {
                    if (isRunning) {
                        alert("Please wait until the pipeline is finished or stop it before switching to a different configuration");
                    } else if (histories.length > 0) {
                        if (confirm("Make sure your current configuration is saved before going back to history")) {
                            configfile = undefined;
                            storedConfigfile.set(undefined);
                        }
                    } else {
                        alert("No history available")
                    }
                }}
                icon={DirectionLoopLeftFilled}
                iconDescription="Back to History"></Button>
        {/if}
    </div>
</header>

<style>
    div.wizard-desc {
        display: flex;
        align-items: center;
        margin-bottom: 0.7rem;
        gap: 0.5rem;
    }
    div.wizard-desc a {
        color: #cadeff;
        text-decoration: none;
    }
    header {
        grid-area: header;
        padding: 1rem 2rem 2rem 2rem;
        background-color: #000000;
        color: #ffffff;
        display: grid;
        grid-template-columns: 1fr auto;
        grid-template-areas: "left right";
        align-items: center;
    }
    div.header-left {
        grid-area: left;
    }
    div.header-right {
        grid-area: right;
        text-align: right;
    }
    h1 {
        font-size: 2rem;
        font-weight: 600;
        margin: 0;
        padding-bottom: 0.4rem;
    }
</style>
