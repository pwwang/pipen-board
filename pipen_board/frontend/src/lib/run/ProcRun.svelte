<script>
    import InlineNotification from "carbon-components-svelte/src/Notification/InlineNotification.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import TreeView from "carbon-components-svelte/src/TreeView/TreeView.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import Tag from "carbon-components-svelte/src/Tag/Tag.svelte";
    import Reset from "carbon-icons-svelte/lib/Reset.svelte";

    import { JOB_TAG_KIND } from "../constants";
    import FilePreview from "./FilePreview.svelte";

    export let status;
    export let proc;
    // job rcs
    export let jobs;

    // selected jobs
    let job;
    // job tree
    let jobTree = [];
    // selected tree nodes
    // let treeActiveId = "";
    // let treeSelectedIds = [];
    // let treeExpandedIds = [];
    // $: console.table({treeActiveId, treeSelectedIds, treeExpandedIds})
    // error
    let toastNotify = { kind: undefined, subtitle: undefined };
    // loading
    let fetching = false;
    // file details
    let fileDetails;
    let fetchingFile = false;

    // dragging
    let dragStartX = null;
    let dragStartY = null;
    let initWidth = null;
    let initHeight = null;

    // file selected in the tree
    let fileSelected = null;

    const handleDragStartX = function (e) {
        dragStartX = e.clientX;
        initWidth = e.target.previousElementSibling.clientWidth;
    };

    const handleDragStartY = function (e) {
        dragStartY = e.clientY;
        initHeight = e.target.previousElementSibling.clientHeight;
    };

    const handleDrag = function (e) {
        if (dragStartX !== null) {
            e.stopPropagation();
            e.preventDefault();
            const dx = e.clientX - dragStartX;
            const width = initWidth + dx < 0 ? 0 : initWidth + dx;
            document.getElementById("procrun-wrap").style.setProperty("--tree-width", `${width}px`);
        } else if (dragStartY !== null) {
            e.stopPropagation();
            e.preventDefault();
            const dy = e.clientY - dragStartY;
            const height = initHeight + dy < 0 ? 0 : initHeight + dy;
            document.getElementById("procrun-wrap").style.setProperty("--jobs-height", `${height}px`);
        }
    };

    const handleDragEnd = function () {
        dragStartX = null;
        dragStartY = null;
    };

    const loadJobTree = async function (jobid) {
        // unload previous job tree
        let loadedJobTree = [];
        // reset tree selection does not work
        // treeActiveId = "";
        // treeSelectedIds = [];
        // treeExpandedIds = [];
        fileDetails = undefined;
        toastNotify.kind = "info";
        toastNotify.subtitle = "Loading job details...";
        fetching = true;
        let response = {};
        try {
            response = await fetch("/api/job/get_tree", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ proc, job: jobid }),
            })
        } catch (error) {
            response.statusText = error;
        } finally {
            fetching = false;
        }
        if (!response.ok) {
            toastNotify.kind = "error";
            toastNotify.subtitle = `Failed to get job details: ${response.status} ${response.statusText}`;
        } else {
            toastNotify.kind = undefined;
            loadedJobTree = await response.json();
        }
        return loadedJobTree;
    };
    if (jobs.length === 1) {
        job = 0;
        loadJobTree(0).then(t => { jobTree = t; });
    }

    const loadFileDetails = async (e) => {
        // {expanded, id, leaf, text}
        if (!e.detail.leaf) {
            return;
        }
        if (fetchingFile) {
            toastNotify.kind = "error";
            toastNotify.subtitle = "Fetching another file, please wait...";
            return;
        }
        const findItem = function(items, id) {
            for (const item of items) {
                if (item.id === id) {
                    return item;
                }
                if (item.children) {
                    const found = findItem(item.children, id);
                    if (found) {
                        return found;
                    }
                }
            }
        };
        // find the full path in job tree
        fileSelected = e.detail.id;
        loadFileDetailsById();
    };

    const loadFileDetailsById = async () => {
        if (!fileSelected) {
            return;
        }
        const findItem = function(items, id) {
            for (const item of items) {
                if (item.id === id) {
                    return item;
                }
                if (item.children) {
                    const found = findItem(item.children, id);
                    if (found) {
                        return found;
                    }
                }
            }
        };
        const item = findItem(jobTree, fileSelected);
        // unlikely to happen
        if (!item) {
            toastNotify.kind = "error";
            toastNotify.subtitle = "Failed to find the file path";
            fetchingFile = false;
            return;
        }
        let response = {};
        try {
            response = await fetch("/api/job/get_file", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ proc, job, path: item.full }),
            })
        } catch (error) {
            response.statusText = error;
        } finally {
            fetchingFile = false;
        }
        if (!response.ok) {
            toastNotify.kind = "error";
            toastNotify.subtitle = `Failed to get file details: ${response.status} ${response.statusText}`;
        } else {
            fileDetails = { ...await response.json(), path: item.full, text: item.text};
        }
    };

</script>

<svelte:window
    on:mouseup={handleDragEnd}
    on:mousemove={handleDrag} />

{#if status === "init"}
<div class="center-wrapper">
    <InlineNotification
        lowContrast
        kind="warning"
        hideCloseButton
    >This process has not been run yet or unknown errors occurred.</InlineNotification>
</div>
{:else}
<div class="procrun-wrap" id="procrun-wrap" style="{jobs.length === 1 ? '--jobs-height: 0' : ''}">
    <div class="jobs">
        <div class="joblist">
            {#each jobs as j, i (i)}
                <Tag
                    interactive
                    disabled={fetching}
                    on:click={async (e) => {job = i; jobTree = await loadJobTree(i);}}
                    class="{i === job ? 'selected' : ''} {j === 'running' ? 'running' : ''}"
                    type="{JOB_TAG_KIND[j] || 'red'}"
                    size="sm">{i}
                </Tag>
            {/each}
        </div>
    </div>
    <div class="draggable row" on:mousedown={handleDragStartY}></div>
    <div class="tree {jobs[job] || ''}">
        {#if job !== undefined}
        <TreeView
            labelText="Job #{job}"
            on:select={loadFileDetails}
            children={jobTree}
            />
        <div class="jft-reloader">
            <Button
                on:click={async () => {jobTree = await loadJobTree(job);}}
                size="small"
                kind="ghost"
                tooltipPosition="left"
                tooltipAlignment="start"
                iconDescription="Reload file tree"
                icon={Reset} />
        </div>
        {:else}
        File tree view
        {/if}
    </div>
    <div class="draggable" on:mousedown={handleDragStartX}></div>
    <div class="details">
        <div class="jobdetail">
            {#if job === undefined}
            <div class="center-wrapper">
                <InlineNotification
                    lowContrast
                    kind="info"
                    hideCloseButton
                >Please select a job to view its details.</InlineNotification>
            </div>
            {:else if !fileDetails}
                <div class="center-wrapper">
                    <InlineNotification
                        lowContrast
                        kind="info"
                        hideCloseButton
                    >Select a file to preview</InlineNotification>
                </div>
            {:else}
                <FilePreview {proc} {job} reloadFileDetails={loadFileDetailsById} info={fileDetails} />
            {/if}
        </div>
    </div>
</div>
{/if}

{#if toastNotify.kind}
    <ToastNotification
        lowContrast
        kind={toastNotify.kind}
        timeout={3000}
        on:close={() => (toastNotify.kind = undefined)}
        caption={new Date().toLocaleString()}
    >
    <div slot="subtitle">{@html toastNotify.subtitle}</div>
    </ToastNotification>
{/if}

<style>
    div.procrun-wrap {
        --tree-width: 15rem;
        --jobs-height: 3.8rem;
        display: grid;
        grid-template-areas:
            "jobs jobs jobs"
            "draggable-row draggable-row draggable-row"
            "tree draggable details";
        grid-template-columns: var(--tree-width) .5rem auto;
        grid-template-rows: var(--jobs-height) .5rem auto;
        height: 100%;
    }
    div.procrun-wrap div.jobs {
        grid-area: jobs;
        overflow-y: auto;
    }
    div.procrun-wrap div.draggable.row {
        grid-area: draggable-row;
    }
    div.procrun-wrap div.tree {
        grid-area: tree;
        overflow-y: auto;
        padding: 1rem;
        position: relative;
    }
    div.procrun-wrap div.tree div.jft-reloader {
        position: absolute;
        top: 0;
        right: 0;
        padding: 1rem;
        transform: scale(.8);
    }
    div.procrun-wrap div.draggable {
        grid-area: draggable;
    }
    div.procrun-wrap div.joblist {
        display: flex;
        flex-wrap: wrap;
        margin: 1rem 0.8rem;
    }
    div.procrun-wrap div.details {
        grid-area: details;
        height: 100%;
        background-color: #f7f7f7;
        display: flex;
    }
    div.procrun-wrap div.jobdetail {
        height: 100%;
        width: 100%;
    }
</style>