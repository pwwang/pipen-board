<script>
    // Used by ../App.svelte
    import DataTable from "carbon-components-svelte/src/DataTable/DataTable.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import TextInput from "carbon-components-svelte/src/TextInput/TextInput.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import RowDelete from "carbon-icons-svelte/lib/RowDelete.svelte";
    import SaveModel from "carbon-icons-svelte/lib/SaveModel.svelte";
    import DocumentDownload from "carbon-icons-svelte/lib/DocumentDownload.svelte";
    import GroupObjectsNew from "carbon-icons-svelte/lib/GroupObjectsNew.svelte";
    import Download from "carbon-icons-svelte/lib/Download.svelte";
    import Header from "./Header.svelte";
    import { updateConfigfile, updateErrors, storedGlobalChanged } from "./store";
    import { fetchAPI } from "./utils";

    // example.py:ExamplePipeline
    export let pipeline;
    // [{"name": "ExamplePipeline", "configfile": "/path/to/config", "time": "2021-01-01 00:00:00" }]
    export let histories = [];
    // selected configuration file
    export let configfile;

    let error;
    let deleting;
    let uploading;
    let pipelineName = pipeline.split(":").at(-1);

    const headers = [
        { key: "name", value: "Name" },
        { key: "workdir", value: "Working Directory" },
        { key: "ctime", value: "Created Time" },
        { key: "mtime", value: "Modified Time"},
        { key: "actions", empty: true },
    ];

    $: rows = histories.map((history, i) => {
        return {
            id: i,
            name: history.name,
            workdir: history.workdir,
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
            await fetchAPI("/api/history/del", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ configfile }),
            });
        } catch (e) {
            error = `<strong>Failed to delete history:</strong> <br /><br /><pre>${e}</pre>`;
        } finally {
            deleting = undefined;
        }
        if (!error) {
            histories = histories.filter((_, j) => j !== i);
        }
    };

    const history_saveas = async (i, configfile) => {
        const name = prompt("Please enter a new name for this configuration: \n\n" + configfile);
        if (!name) {
            deleting = undefined;
            return;
        }

        let resp;
        try {
            resp = await fetchAPI("/api/history/saveas", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ configfile, new_name: name }),
            });
            if (resp.error) {
                throw new Error(resp.error);
            }
        } catch (e) {
            error = `<strong>Failed to save configuration with a new name:</strong> <br /><br /><pre>${e}</pre>`;
        } finally {
            deleting = undefined;
        }
        if (!error) {
            const existedHistory = histories.find(h => h.configfile === resp.configfile);
            if (existedHistory) {
                histories = [
                    ...histories.filter(h => h.configfile !== resp.configfile),
                    {...existedHistory, ...resp}
                ]
            } else {
                histories = [...histories, resp];
            }
        }
    };

    const history_download = async (i, configfile) => {
        let resp;
        try {
            resp = await fetchAPI("/api/history/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ configfile }),
            }, "blob");
        } catch (e) {
            error = `<strong>Failed to download the schema file:</strong> <br /><br /><pre>${e}</pre>`;
        } finally {
            deleting = undefined;
        }
        const blob = new Blob([resp], { type: "text/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = histories[i].name + ".schema.json";
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    const openSchemaFile = () => {
        const input = document.getElementById("schema_file");
        // @ts-ignore
        input.value = "";
        input.click();
    };

    const loadSchemaFile = async (e) => {
        uploading = true;
        const target = e.target;
        if (target.files.length === 0) {
            uploading = false;
            return;
        }
        // Upload the file and come back with the new history item with
        // the name in the file and current working directory
        const formData = new FormData();
        formData.append("schema_file", target.files[0]);
        let resp;
        try {
            resp = await fetchAPI("/api/history/upload", {
                method: "POST",
                body: formData,
            });
            if (resp.error) {
                throw new Error(resp.error);
            }
        } catch (e) {
            error = `<strong>Failed to upload the schema file:</strong> <br /><br /><pre>${e}</pre>`;
        } finally {
            uploading = false;
        }
        if (!error) {
            histories = [...histories, resp];
        }
    };

    const loadFromURL = async (event) => {
        // if key is Enter, try upload
        // otherwise, do nothing
        if (event.key !== "Enter") {
            return;
        }
        if (uploading) {
            error = "Please wait for the previous upload to finish.";
            return;
        }
        const url = event.target.value;
        if (!url) {
            return;
        }
        uploading = true;
        let resp;
        try {
            resp = await fetchAPI("/api/history/fromurl", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ url }),
            });
            if (resp.error) {
                throw new Error(resp.error);
            }
        } catch (e) {
            error = `<strong>Failed to upload the schema file:</strong> <br /><br /><pre>${e}</pre>`;
        } finally {
            uploading = false;
        }
        if (!error) {
            histories = [...histories, resp];
            event.target.value = "";
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
    <Header {pipelineName} />
    <div class="new-inst">
        <Button
            kind="primary"
            icon={GroupObjectsNew}
            iconDescription="Create a New Instance"
            on:click={() => {
                let new_name = prompt(
                    "Please enter a name for the new instance:\n\n" +
                    `- Leave it empty to use the default name (${pipelineName})\n`
                );
                if (new_name === null) {
                    error = `Cancelled creating a new instance.`;
                    return;
                }
                if (new_name === "") {
                    new_name = pipelineName;
                }
                if (histories.find(h => h.is_current && h.name === new_name)) {
                    error = `The name "${new_name}" is already used under current working directory.`;
                    return;
                }
                // Set globalChanged to false
                storedGlobalChanged.set(false);
                // Clear up the errors
                updateErrors({});
                updateConfigfile(undefined);
                configfile = `new:${new_name}`;
            }}
            size="small">
            Create a New Instance
        </Button> /
        <Button
            kind="secondary"
            icon={DocumentDownload}
            iconDescription="Load From a Schema File"
            on:click={openSchemaFile}
            disabled={uploading}
            size="small">
            Load From a Schema File ...
        </Button> /
        <TextInput on:keyup={loadFromURL} placeholder="Load Schema File from a URL (Enter to confirm)" light hideLabel  /> /
        <span>or load from a saved configuration:</span>
        <input type="file" id="schema_file" on:change={loadSchemaFile} style="display: none;" />
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
                        disabled={deleting === cell.value[0] || !histories[cell.value[0]].is_current}
                        on:click={() => {
                            storedGlobalChanged.set(false);
                            updateErrors({});
                            updateConfigfile(cell.value[1]);
                            configfile = cell.value[1];
                        }}
                        >Load</Button>
                    <Button
                        size="small"
                        kind="tertiary"
                        icon={SaveModel}
                        iconDescription="Save the configuration as a new one"
                        disabled={deleting === cell.value[0]}
                        on:click={() => {
                            deleting = cell.value[0];
                            history_saveas(...cell.value);
                        }}
                        >Save As</Button>
                    <Button
                        size="small"
                        kind="tertiary"
                        icon={Download}
                        iconDescription="Download the schema file"
                        disabled={deleting === cell.value[0]}
                        on:click={() => {
                            deleting = cell.value[0];
                            history_download(...cell.value);
                        }}
                        >Download</Button>
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
