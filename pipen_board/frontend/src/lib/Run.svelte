<script>
    // Used by Layout.svelte
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import InlineNotification from "carbon-components-svelte/src/Notification/InlineNotification.svelte";
    import InlineLoading from "carbon-components-svelte/src/InlineLoading/InlineLoading.svelte";
    import Tile from "carbon-components-svelte/src/Tile/Tile.svelte";
    import StopFilled from "carbon-icons-svelte/lib/StopFilled.svelte";
    import Redo from "carbon-icons-svelte/lib/Redo.svelte";
    import NavItem from "./configuration/NavItem.svelte";
    import NavDivider from "./configuration/NavDivider.svelte";
    import ProcRun from "./run/ProcRun.svelte";
    import Log from "./run/Log.svelte";
    import { SECTION_PROCESSES, SECTION_PROCGROUPS, SECTION_DIAGRAM, SECTION_REPORTS, SECTION_LOG } from "./constants.js";
    import { getStatusPercentage, fetchAPI } from "./utils";

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
    export let runStarted;
    // reactive
    export let finished;

    // if we are fetching the inital data
    let fetching = true;
    // which item is selected
    let activeNavItem;
    // toast notification
    let toastNotify = { kind: undefined, subtitle: undefined, timeout: 0 };
    // whether we have a first update from running data
    let firstUpdate = true;
    // whether we are re-running or stopping
    let rerunningOrStopping = false;
    // the log of building the report
    let report_building_log = "Click 'building log' above to load.";

    if (runStarted > 0) {
        // fetch the updated running data
        data = undefined;
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onopen = function() {
            ws.send(JSON.stringify({ type: "connect", client: "web" }));
        };
        ws.onmessage = async function(event) {
            data = JSON.parse(event.data);
            fetching = false;
            finished = data.FINISHED;
            statusPercent = getStatusPercentage(data);
            if (firstUpdate) {
                firstUpdate = false;
                activeNavItem = "Log";
            }
        }
    }

    const changeStatus = (newst, oldst = null) => {
        // change the status of the processes and jobs in data
        for (const [k, v] of Object.entries(data[SECTION_PROCESSES])) {
            if (v.status === oldst || oldst === null) {
                v.status = newst;
            }
            v.jobs = v.jobs.map((v2) => (v2 === oldst || oldst === null) ? newst : v2);
        }

        for (const [k, v] of Object.entries(data[SECTION_PROCGROUPS])) {
            for (const [k2, v2] of Object.entries(v)) {
                if (v2.status === oldst || oldst === null) {
                    v2.status = newst;
                }
                v2.jobs = v2.jobs.map((v3) => (v3 === oldst || oldst === null) ? newst : v3);
            }
        }
        // trigger the reactivity
        data = data;
    }

    const rerun = async () => {
        if (!confirm("Are you sure to re-run this pipeline (using the same configurations)?")) {
            return;
        }
        rerunningOrStopping = true;
        let d;
        try {
            d = await fetchAPI("/api/pipeline/rerun", { method: "POST" });
        } catch (e) {
            toastNotify = { kind: "error", subtitle: `Run re-submission failed: ${e}.`, timeout: 5000 };
        } finally {
            rerunningOrStopping = false;
        }
        if (toastNotify.kind !== "error") {
            if (d.ok) {
                toastNotify = { kind: "success", subtitle: "Run re-submitted successfully.", timeout: 5000 };
                finished = false;
                statusPercent = [0, 0, 0, 100];
                // change the status of the processes and jobs in data
                changeStatus("init");
                data[SECTION_LOG] = "";
                activeNavItem = "Log";
            } else {
                toastNotify = { kind: "error", subtitle: `Run re-submission failed: ${d.msg}.`, timeout: 5000 };
            }
        }
    }

    const stoprun = async () => {
        if (!confirm("Are you sure to stop the run?")) {
            return;
        }
        rerunningOrStopping = true;
        let d;
        try {
            d = await fetchAPI("/api/pipeline/stop", { method: "POST" });
        } catch (e) {
            toastNotify = { kind: "error", subtitle: `Run stop failed: ${e}.`, timeout: 5000 };
        } finally {
            rerunningOrStopping = false;
        }
        if (toastNotify.kind !== "error") {
            if (d.ok) {
                toastNotify = { kind: "success", subtitle: "Run stopped successfully.", timeout: 5000 };
                finished = true;
                statusPercent = [statusPercent[0], statusPercent[1] + statusPercent[2], 0, statusPercent[3]];
                // change the status of the processes and jobs in data
                changeStatus("failed", "running");
            } else {
                toastNotify = { kind: "error", subtitle: `Run stop failed: ${d.msg}.`, timeout: 5000 };
            }
        }
    }

    const loadReportBuildingLog = async () => {
        report_building_log = 'Loading ...';
        let d;
        try {
            d = await fetchAPI("/api/report_building_log");
        } catch (e) {
            report_building_log = `Error: ${e}`;
        }
        if (d) {
            report_building_log = d.ok ? (d.content || '(empty)') : `Error: ${d.msg}`;
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

{#if runStarted > 0}
<div class="running-control">
    {#if finished}
        <Button disabled={rerunningOrStopping} size="small" kind="primary" icon={Redo} on:click={rerun}>Re-Run</Button>
    {:else}
        <Button disabled={rerunningOrStopping} size="small" kind="danger" icon={StopFilled} on:click={stoprun}>
            {rerunningOrStopping ? "Stopping" : "Stop"}
        </Button>
    {/if}
</div>
{/if}
<div class="run-container">
    <aside class="run-nav">

        {#if data[SECTION_LOG] !== null}
            <NavItem text="Log" noerror bind:activeNavItem />
        {/if}
        {#if data[SECTION_DIAGRAM]}
            <NavItem text="Diagram" noerror bind:activeNavItem />
        {/if}
        {#if data[SECTION_REPORTS]}
            <NavItem text="Reports" noerror bind:activeNavItem />
        {/if}
        {#if data[SECTION_PROCESSES] && Object.keys(data[SECTION_PROCESSES]).length > 0}
            <NavDivider group="processes" />
            {#each Object.keys(data[SECTION_PROCESSES]).sort((a, b) => data[SECTION_PROCESSES][a].order - data[SECTION_PROCESSES][b].order) as proc}
                <NavItem class="run-status-{data[SECTION_PROCESSES][proc].status}" noerror text={proc} sub bind:activeNavItem />
            {/each}
        {/if}
        {#if data[SECTION_PROCGROUPS]}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as procgroup}
                <NavDivider group="group: {procgroup}" />
                {#each Object.keys(data[SECTION_PROCGROUPS][procgroup]).sort((a, b) => data[SECTION_PROCGROUPS][procgroup][a].order - data[SECTION_PROCGROUPS][procgroup][b].order) as proc}
                    <NavItem class="run-status-{data[SECTION_PROCGROUPS][procgroup][proc].status}" noerror sub text={proc} bind:activeNavItem />
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
                <div class="reports-wrapper-layout">
                    <Tile>
                        <div class="reports-wrapper">
                            <p>Reports are generated at <code>{data[SECTION_REPORTS]}</code></p>
                            <p>&nbsp;</p>
                            <p>You can either:</p>
                            <ul>
                                <li>Check them out by directly visiting <code>{data[SECTION_REPORTS]}/index.html</code></li>
                                <li>Run <code>pipen report serve -r {data[SECTION_REPORTS].substring(0, data[SECTION_REPORTS].lastIndexOf('/'))}</code>, and go to <code>REPORTS</code> directory.</li>
                                <li>Visit <a target="_blank" href="/reports/{data[SECTION_REPORTS].replaceAll('/', '|')}/REPORTS/index.html">the reports</a> served by this plugin</li>
                                <li>Or check the
                                    <a href={'javascript:void(0)'} on:click|preventDefault={loadReportBuildingLog}>building log</a>
                                    if necessary.
                                </li>
                            </ul>
                            <p>&nbsp;</p>
                            <p>Note that if the run fails, the reports may be incomplete.</p>
                        </div>
                    </Tile>
                    <Log log={report_building_log} />
                </div>
            </div>
        {:else if activeNavItem in data[SECTION_PROCESSES]}
            {#key activeNavItem}
            <ProcRun
                status={data[SECTION_PROCESSES][activeNavItem].status}
                proc={activeNavItem}
                jobs={data[SECTION_PROCESSES][activeNavItem].jobs}
            />
            {/key}
        {:else if activeNavItem}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as procgroup}
                {#if activeNavItem in data[SECTION_PROCGROUPS][procgroup]}
                    {#key activeNavItem}
                    <ProcRun
                        status={data[SECTION_PROCGROUPS][procgroup][activeNavItem].status}
                        proc={activeNavItem}
                        jobs={data[SECTION_PROCGROUPS][procgroup][activeNavItem].jobs}
                    />
                    {/key}
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
                    <p>There may be also extra processes or process groups that are not in the pipeline by current configuration, but were run in the previous run with a different configuration.</p>
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
    div.running-control {
        position: absolute;
        bottom: 1rem;
        text-align: center;
        z-index: 999;
        width: 20rem;
    }
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
    div.reports-wrapper-layout {
        display: flex;
        flex-flow: column;
        height: 100%;
        gap: 1rem;
    }
    div.reports-wrapper-layout > :global(div.bx--tile) {
        min-height: auto !important;
    }
    div.reports-wrapper-layout > :global(div.run-log) {
        flex-grow: 1;
    }
    div.reports-wrapper-layout > :global(div.run-log > div.run-log__code) {
        height: 100%;
        overflow: auto;
    }
</style>
