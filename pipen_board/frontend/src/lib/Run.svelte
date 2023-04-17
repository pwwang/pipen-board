<script>
    // Used by Layout.svelte
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import InlineNotification from "carbon-components-svelte/src/Notification/InlineNotification.svelte";
    import InlineLoading from "carbon-components-svelte/src/InlineLoading/InlineLoading.svelte";
    import Tile from "carbon-components-svelte/src/Tile/Tile.svelte";
    import NavItem from "./configuration/NavItem.svelte";
    import NavDivider from "./configuration/NavDivider.svelte";
    import ProcRun from "./run/ProcRun.svelte";
    import Log from "./run/Log.svelte";
    import { SECTION_PROCESSES, SECTION_PROCGROUPS, SECTION_DIAGRAM, SECTION_REPORTS, SECTION_LOG } from "./constants.js";
    import { getStatusPercentage } from "./utils";

    // {
    //    LOG, DIAGRAM, REPORTS,
    //    PROCESSES => {
    //        proc -> { status, jobs: [status] }
    //    },
    //    PROCGROUPS => {
    //        pg -> {
    //            proc -> { status, jobs: [status] }
    //        }
    //    }
    // }
    // proc status: init, running, succeeded, failed
    // job status: init, queued, submitted, running, killed, succeeded, failed
    export let data;
    // reactive
    export let statusPercent;
    // reactive
    export let isRunning;

    // if we are fetching the inital data
    let fetching = true;
    // which item is selected
    let activeNavItem;
    // toast notification
    let toastNotify = { kind: undefined, subtitle: undefined, timeout: 0 };

    if (isRunning > 0) {
        // fetch the updated running data
        data = undefined;
        let firstUpdate = true;
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onopen = function() {
            ws.send(JSON.stringify({ type: "connect", client: "web" }));
        };
        ws.onmessage = async function(event) {
            data = JSON.parse(event.data);
            fetching = false;
            statusPercent = getStatusPercentage(data);
            if (firstUpdate) {
                firstUpdate = false;
                activeNavItem = "Log";
            }
        }
    }

</script>

{#if !data && fetching}
<div class="center-wrapper">
    <InlineLoading description="Collecting information of the run ..." />
</div>
{:else if Object.keys(data || {}).length === 0}
<div class="center-wrapper">
    <InlineNotification
        lowContrast
        kind="warning"
        hideCloseButton
    >No data found for this run.</InlineNotification>
</div>
{:else}
<div class="run-container">
    <aside class="run-nav">
        {#if data[SECTION_LOG] !== null}
            <NavItem text="Log" bind:activeNavItem />
        {/if}
        {#if data[SECTION_DIAGRAM]}
            <NavItem text="Diagram" bind:activeNavItem />
        {/if}
        {#if data[SECTION_REPORTS]}
            <NavItem text="Reports" bind:activeNavItem />
        {/if}
        {#if data[SECTION_PROCESSES] && Object.keys(data[SECTION_PROCESSES]).length > 0}
            <NavDivider group="processes" />
            {#each Object.keys(data[SECTION_PROCESSES]) as proc}
                <NavItem class="run-status-{data[SECTION_PROCESSES][proc].status}" text={proc} sub bind:activeNavItem />
            {/each}
        {/if}
        {#if data[SECTION_PROCGROUPS]}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as procgroup}
                <NavDivider group="group: {procgroup}" />
                {#each Object.keys(data[SECTION_PROCGROUPS][procgroup]) as proc}
                    <NavItem class="run-status-{data[SECTION_PROCGROUPS][procgroup][proc].status}" sub text={proc} bind:activeNavItem />
                {/each}
            {/each}
        {/if}
    </aside>
    <main>
        {#if activeNavItem === "Log"}
            <div class="run-main">
                <Log log={data[SECTION_LOG]} />
            </div>
        {:else if activeNavItem === "Diagram"}
            <div class="run-main">
                {@html data[SECTION_DIAGRAM]}
            </div>
        {:else if activeNavItem === "Reports"}
            <div class="run-main">
                <Tile>
                    <div class="reports-wrapper">
                        <p>Reports are generated at <code>{data[SECTION_REPORTS]}</code></p>
                        <p>&nbsp;</p>
                        <p>You can either:</p>
                        <ul>
                            <li>Check them out by directly visiting <code>{data[SECTION_REPORTS]}/index.html</code></li>
                            <li>Or run <code>pipen report serve -r {data[SECTION_REPORTS].substring(0, data[SECTION_REPORTS].lastIndexOf('/'))}</code>, and go to <code>REPORTS</code> directory.</li>
                        </ul>
                        <p>&nbsp;</p>
                        <p>Note that if the run fails, the reports may be incomplete.</p>
                    </div>
                </Tile>
            </div>
        {:else if activeNavItem in data[SECTION_PROCESSES]}
            <ProcRun
                status={data[SECTION_PROCESSES][activeNavItem].status}
                proc={activeNavItem}
                jobs={data[SECTION_PROCESSES][activeNavItem].jobs}
            />
        {:else if activeNavItem}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as procgroup}
                {#if activeNavItem in data[SECTION_PROCGROUPS][procgroup]}
                    <ProcRun
                        status={data[SECTION_PROCGROUPS][procgroup][activeNavItem].status}
                        proc={activeNavItem}
                        jobs={data[SECTION_PROCGROUPS][procgroup][activeNavItem].jobs}
                    />
                {/if}
            {/each}
        {:else if data[SECTION_LOG] === null}
            <div class="center-wrapper">
                <InlineNotification
                    lowContrast
                    kind="warning"
                    hideCloseButton
                >
                    <p>No previous run found.</p>
                </InlineNotification>
            </div>
        {:else}
            <div class="center-wrapper">
                <InlineNotification
                    lowContrast
                    kind="info"
                    hideCloseButton
                >
                    <p>Select an item from the navigation menu on the left to view its details.</p>
                    <p style="flex-basis: 100%;">&nbsp;</p>
                    <p>Note that the information may be incomplete for the previous run if it was failed, since the information was gather from the working directory instead of the pipeline (<code>Pipen</code>) object.</p>
                </InlineNotification>
            </div>
        {/if}
    </main>
</div>
{/if}

{#if toastNotify.kind}
    <ToastNotification
        lowContrast
        kind={toastNotify.kind}
        timeout={toastNotify.timeout}
        on:close={() => (toastNotify.kind = undefined)}
        caption={new Date().toLocaleString()}
    >
    <div slot="subtitle">{@html toastNotify.subtitle}</div>
    </ToastNotification>
{/if}

<style>
    div.run-container {
        height: 100%;
        display: grid;
        grid-template-columns: 20rem auto;
        grid-template-areas:
            "nav main"
    }
    aside.run-nav {
        grid-area: nav;
        grid-auto-flow: column;
        padding: 2rem 0;
        background-color: #f4f4f4;
        overflow: auto;
    }
    main {
        grid-area: main;
        grid-auto-flow: column;
        background-color: #e6e6e6;
        overflow: auto;
        height: 100%;
    }
    main div.run-main {
        padding: 2rem;
        height: 100%;
    }
    div.reports-wrapper * {
        font-size: 1rem;
        line-height: 1.5rem;
    }
    div.reports-wrapper ul {
        list-style-type: circle;
        list-style-position: inside;
    }
    div.reports-wrapper code {
        background-color: #4f4f4f;
        padding: 0.2rem 0.4rem;
        border-radius: 0.2rem;
        color: white;
        line-height: .8rem;
        font-size: .8rem;
    }
</style>