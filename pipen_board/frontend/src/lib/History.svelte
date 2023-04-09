<script>
    // Used by ../App.svelte
    import DataTable from "carbon-components-svelte/src/DataTable/DataTable.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import RowDelete from "carbon-icons-svelte/lib/RowDelete.svelte";
    import DocumentDownload from "carbon-icons-svelte/lib/DocumentDownload.svelte";
    import GroupObjectsNew from "carbon-icons-svelte/lib/GroupObjectsNew.svelte";
    import Header from "./Header.svelte";
    import { updateConfigfile, updateErrors } from "./store";

    // example.py:ExamplePipeline
    export let pipeline;
    // [{"name": "ExamplePipeline", "configfile": "/path/to/config", "time": "2021-01-01 00:00:00" }]
    export let histories = [];
    // selected configuration file
    export let configfile;

    let error;
    let deleting;

    const headers = [
        { key: "name", value: "Name" },
        { key: "configfile", value: "Config File" },
        { key: "ctime", value: "Created Time" },
        { key: "mtime", value: "Modified Time"},
        { key: "actions", empty: true },
    ];

    $: rows = histories.map((history, i) => {
        return {
            id: i,
            name: history.name,
            configfile: history.configfile,
            ctime: history.ctime,
            mtime: history.mtime,
            actions: [i, history.configfile]
        }
    });

    const history_del = async (i, configfile) => {
        if (confirm("Are you sure to delete this history?\n\n" + configfile) === false) {
            deleting = undefined;
            return;
        }

        try {
            const fetched = await fetch("/api/history/del", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ configfile }),
            });
            if (!fetched.ok)
                throw new Error(`${fetched.status} ${fetched.statusText}`);
        } catch (e) {
            error = `<strong>Failed to delete history:</strong> <br /><br /><pre>${e.stack}</pre>`;
        } finally {
            deleting = undefined;
        }
        if (!error) {
            histories = histories.filter((_, j) => j !== i);
        }
    };

</script>

{#if error}
    <ToastNotification
        lowContrast
        kind="error"
        title="Error"
        timeout={3000}
        on:close={() => { error = undefined; }}
        caption={new Date().toLocaleString()}
    >
    <div slot="subtitle">{@html error}</div>
    </ToastNotification>
{/if}

<div class="history-wrapper">
    <Header {histories} pipelineName={pipeline.split(":").at(-1)} />
    <div class="new-inst">
        <Button
            kind="primary"
            icon={GroupObjectsNew}
            iconDescription="Create a New Instance"
            on:click={() => {
                updateErrors({});
                updateConfigfile("");
                configfile = null;
            }}
            size="small">
            Create a New Instance
        </Button>
        <span>or load from a saved configuration:</span>
    </div>

    <div class="pipen-history">
        <DataTable
            zebra
            sortable
            sortKey="mtime"
            sortDirection="descending"
            title="Saved configurations"
            description={`For pipeline: ${pipeline}`}
            {headers}
            {rows}
            size="medium">
            <svelte:fragment slot="cell" let:cell>
                {#if cell.key === "actions"}
                    <Button
                        size="small"
                        kind="tertiary"
                        icon={DocumentDownload}
                        iconDescription="Load the configuration"
                        disabled={deleting === cell.value[0]}
                        on:click={() => {
                            updateErrors({});
                            updateConfigfile(cell.value[1]);
                            configfile = cell.value[1];
                        }}
                        >Load</Button>
                    <Button
                        size="small"
                        kind="danger-tertiary"
                        icon={RowDelete}
                        iconDescription="Delete the history"
                        disabled={deleting === cell.value[0]}
                        on:click={() => {
                            deleting = cell.value[0];
                            history_del(...cell.value);
                        }}
                        >Delete</Button>
                {:else}
                    {cell.value}
                {/if}
            </svelte:fragment>
        </DataTable>
    </div>
    </div>

<style>
    div.new-inst {
        grid-area: new-inst;
        margin-top: 2rem;
        display: flex;
        flex-direction: row;
        align-items: center;
        column-gap: 1rem;
        margin-bottom: 1rem;
        padding-left: 15%;
        padding-right: 15%;
    }
    div.pipen-history {
        grid-area: history;
        margin-bottom: 2rem;
        padding-left: 15%;
        padding-right: 15%;
        overflow-y: auto;
    }
    div.history-wrapper {
        height: 100vh;
        display: grid;
        grid-template-areas:
            "header"
            "new-inst"
            "history";
        grid-template-rows: auto auto 1fr;
    }
    div.pipen-history :global(table tr td:last-of-type) {
        white-space: nowrap;
    }
    @media (max-width: 1200px) {
        div.pipen-history {
            padding-left: 5%;
            padding-right: 5%;
        }
        div.new-inst {
            padding-left: 5%;
            padding-right: 5%;
        }
    }
    @media (max-width: 1000px) {
        div.pipen-history :global(table tr th:nth-child(2)) {
            display: none;
        }
        div.pipen-history :global(table tr td:nth-child(2)) {
            display: none;
        }
        div.pipen-history :global(table tr td:last-of-type) {
            white-space: unset;
        }
    }
</style>
