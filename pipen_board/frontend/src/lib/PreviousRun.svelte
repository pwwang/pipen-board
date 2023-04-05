<script>
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import InlineNotification from "carbon-components-svelte/src/Notification/InlineNotification.svelte";
    import InlineLoading from "carbon-components-svelte/src/InlineLoading/InlineLoading.svelte";
    import Tile from "carbon-components-svelte/src/Tile/Tile.svelte";
    import NavItem from "./configuration/NavItem.svelte";
    import NavDivider from "./configuration/NavDivider.svelte";
    import ProcRun from "./run/ProcRun.svelte";
    import { SECTION_PROCESSES, SECTION_PROCGROUPS } from "./constants.js";
    import { IS_DEV } from "./utils";

    export let selected;
    export let configfile;
    export let prev_success;

    let data;
    let fetching = true;
    let toastNotify = { kind: undefined, subtitle: undefined, timeout: 3000 };
    let activeNavItem;
    let statuses = {};

    const loadData = async () => {
        let response = {};
        try {
            response = await fetch("/api/run/prev", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ configfile }),
            });
        } catch (error) {
            response.statusText = error;
        } finally {
            fetching = false;
        }
        if (!response.ok) {
            toastNotify.kind = "error";
            toastNotify.timeout = 0;
            toastNotify.subtitle = `Failed to fetch previous run: ${response.statusText}`;
            return {};
        }
        return await response.json();
    };

    $: if (selected && !data) {
        loadData().then((dat) => {
            data = dat;
            if (IS_DEV) {
                // @ts-ignore
                window.pr_data = data;
            }
            // analyze success, failure, and unrun
            let counts = { success: 0, failure: 0, unrun: 0 };
            for (const proc in data[SECTION_PROCESSES] || {}) {
                if (data[SECTION_PROCESSES][proc].length === 0) {
                    counts.unrun += 1;
                    statuses[proc] = 'unrun';
                } else if (data[SECTION_PROCESSES][proc].every(x => x === 0)) {
                    counts.success += 1;
                    statuses[proc] = 'success';
                } else {
                    counts.failure += 1;
                    statuses[proc] = 'failure';
                }
            }
            for (const pg in data[SECTION_PROCGROUPS] || {}) {
                for (const proc in data[SECTION_PROCGROUPS][pg] || {}) {
                    if (data[SECTION_PROCGROUPS][pg][proc].length === 0) {
                        counts.unrun += 1;
                        statuses[proc] = 'unrun';
                    } else if (data[SECTION_PROCGROUPS][pg][proc].every(x => x === 0)) {
                        counts.success += 1;
                        statuses[proc] = 'success';
                    } else {
                        counts.failure += 1;
                        statuses[proc] = 'failure';
                    }
                }
            }
            const total = counts.success + counts.failure + counts.unrun;
            prev_success = [100 * counts.success / total, 100 * counts.failure / total, 100 * counts.unrun / total]
        });
    }
</script>

{#if fetching}
<div class="center-wrapper">
    <InlineLoading description="Collecting information of previous run ..." />
</div>
{:else if Object.keys(data || {}).length === 0}
<div class="center-wrapper">
    <InlineNotification
        lowContrast
        kind="warning"
        hideCloseButton
    >No data found for previous run.</InlineNotification>
</div>
{:else}
<div class="pr-container">
    <aside class="pr-nav">
        {#if Object.keys(data).includes("diagram")}
            <NavItem text="Diagram" bind:activeNavItem />
        {/if}
        {#if Object.keys(data).includes("reports")}
            <NavItem text="Reports" bind:activeNavItem />
        {/if}
        {#if data[SECTION_PROCESSES] && Object.keys(data[SECTION_PROCESSES]).length > 0}
            <NavDivider group="processes" />
            {#each Object.keys(data[SECTION_PROCESSES]) as proc}
                <NavItem class="pr-status-{statuses[proc]}" text={proc} sub bind:activeNavItem />
            {/each}
        {/if}
        {#if data[SECTION_PROCGROUPS]}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as procgroup}
                <NavDivider group="group: {procgroup}" />
                {#each Object.keys(data[SECTION_PROCGROUPS][procgroup]) as proc}
                    <NavItem class="pr-status-{statuses[proc]}" sub text={proc} bind:activeNavItem />
                {/each}
            {/each}
        {/if}
    </aside>
    <main>
        {#if activeNavItem === "Diagram"}
            <div class="prevrun-main">
                {@html data["diagram"]}
            </div>
        {:else if activeNavItem === "Reports"}
            <div class="prevrun-main">
                <Tile>
                    <div class="reports-wrapper">
                        <p>Reports are generated at <code>{data["reports"]}</code></p>
                        <p>&nbsp;</p>
                        <p>You can either:</p>
                        <ul>
                            <li>Check them out by directly visiting <code>{data["reports"]}/index.html</code></li>
                            <li>Or run <code>pipen report serve -r {data["reports"].substring(0, data["reports"].lastIndexOf('/'))}</code>, and go to <code>REPORTS</code> directory.</li>
                        </ul>
                        <p>&nbsp;</p>
                        <p>Note that if previous run fails, the reports may be incomplete.</p>
                    </div>
                </Tile>
            </div>
        {:else if activeNavItem in data[SECTION_PROCESSES]}
            <ProcRun
                status={statuses[activeNavItem]}
                proc={activeNavItem}
                jobs={data[SECTION_PROCESSES][activeNavItem]}
            />
        {:else if activeNavItem}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as procgroup}
                {#if activeNavItem in data[SECTION_PROCGROUPS][procgroup]}
                    <ProcRun
                        status={statuses[activeNavItem]}
                        proc={activeNavItem}
                        jobs={data[SECTION_PROCGROUPS][procgroup][activeNavItem]}
                    />
                {/if}
            {/each}
        {:else}
            <div class="center-wrapper">
                <InlineNotification
                    lowContrast
                    kind="info"
                    hideCloseButton
                >Select an item from the navigation menu on the left to view its details.</InlineNotification>
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
    div.pr-container {
        height: 100%;
        display: grid;
        grid-template-columns: 20rem auto;
        grid-template-areas:
            "nav main"
    }
    aside.pr-nav {
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
    }
    main div.prevrun-main {
        padding: 2rem;
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