<script>
    import Dashboard from "carbon-icons-svelte/lib/Dashboard.svelte";
    import DirectionLoopLeftFilled from "carbon-icons-svelte/lib/DirectionLoopLeftFilled.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";

    export let pipelineName;
    export let pipelineDesc = undefined;
    export let backToHistory = false;
    export let configfile = undefined;
    export let histories;
</script>

<header>
    <div class="header-left">
        <div class="wizard-desc">
            <Dashboard /> PIPEN BOARD
        </div>
        <h1>{pipelineName}</h1>
        <div>{pipelineDesc ? pipelineDesc : ""}</div>
    </div>
    <div class="header-right">
        {#if backToHistory}
            <Button
                on:click={() => {
                    if (histories.length > 0) {
                        configfile = undefined;
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
