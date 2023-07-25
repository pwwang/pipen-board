<script>
    import copy from "clipboard-copy";
    import hljs from 'highlight.js';
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import InlineNotification from "carbon-components-svelte/src/Notification/InlineNotification.svelte";
    import Copy from "carbon-icons-svelte/lib/Copy.svelte";
    import CopyFile from "carbon-icons-svelte/lib/CopyFile.svelte";
    import TextWrap from "carbon-icons-svelte/lib/TextWrap.svelte";
    import Reset from "carbon-icons-svelte/lib/Reset.svelte";
    import DocumentPreliminary from "carbon-icons-svelte/lib/DocumentPreliminary.svelte";
    import { fetchAPI } from "../utils";
    // {type, path, content}
    export let proc;
    export let job;
    export let info;
    export let reloadFileDetails;

    let fetching = false;
    let wordwrap = false;
    let bigtextShowing = "Head 100";
    let bigtextContent;
    if (info.type === "bigtext") {
        bigtextContent = info.content;
    }

    const bigtextShow = async function(showing) {
        bigtextShowing = showing;

        fetching = true;
        let out;
        try {
            out = await fetchAPI("/api/job/get_file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ proc, job, path: info.path, how: bigtextShowing }),
            })
        } catch (error) {
            alert(`Failed to get file content: ${error}`);
        } finally {
            fetching = false;
        }
        if (out) {
            bigtextContent = out.content;
        }
    };

    const showMetadata = async function() {
        let out;
        try {
            out = await fetchAPI("/api/job/get_file_metadata", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ proc, job, path: info.path }),
            })
        } catch (error) {
            alert(`Failed to get file metadata: ${error}`);
        }
        if (out) {
            let msg = "Meta information of the file:\n\n";
            for (let [key, value] of Object.entries(out)) {
                switch (key) {
                    case "ctime":
                        key = "Created";
                        break;
                    case "mtime":
                        key = "Modified";
                        break;
                    case "size_human":
                        key = "Size";
                        value = `${value} (${out.size.toLocaleString()})`;
                        break;
                    case "name":
                        key = "File Name";
                        break;
                    default:
                        break;
                }
                if (key !== "size") {
                    msg += `${key}: ${value}\n`;
                }
            }
            console.log(out);
            alert(msg);
        }
    };

</script>

<div class="filepreview-wrapper">
    <div class="filepreview-actions">
        <Button size="small" kind="tertiary" icon={Copy} on:click={() => copy(info.path)} iconDescription="Copy File Path" />
        <Button size="small" kind="tertiary" icon={Copy} on:click={() => copy(info.path)} iconDescription="Copy File Path" />
        {#if info.type === "text" }
            <Button size="small" kind="tertiary" icon={CopyFile} on:click={() => copy(info.content)} iconDescription="Copy Content" />
        {:else if info.type === "bigtext"}
            <Button size="small" kind="tertiary" icon={CopyFile} on:click={() => copy(info.content)} iconDescription="Copy Content" />
            {#each ["Head 100", "Head 500", "Tail 100", "Tail 500"] as showing}
                <Button size="small" disabled={bigtextShowing === showing || fetching} kind="tertiary" on:click={e => bigtextShow(showing)}>{showing}</Button>
            {/each}
        {/if}
        <Button size="small" kind="tertiary" icon={DocumentPreliminary} on:click={showMetadata} iconDescription="Show Metadata" />
        <Button
            size="small"
            kind="tertiary"
            icon={Reset}
            on:click={reloadFileDetails}
            iconDescription="Reload the File" />
        {#if info.type === "text"}
        <Button
            size="small"
            kind="ghost"
            icon={TextWrap}
            isSelected={wordwrap}
            on:click={() => {wordwrap = !wordwrap;}}
            iconDescription="Toggle word wrap" />
        {/if}
    </div>
    <div class="filepreview-content scrollable">
        {#if fetching}
            <div class="content-wrapper">Loading ...</div>
        {:else if info.type === "text"}
            {#if info.content === "" || info.content === null}
                <pre class="file-text {wordwrap ? 'text-wrap' : ''}">(empty)<hr /></pre>
            {:else if !info.path.split("/").at(-1).startsWith("job.")}
                <pre class="file-text {wordwrap ? 'text-wrap' : ''}">{info.content}<hr /></pre>
            {:else}
                <pre class="file-text {wordwrap ? 'text-wrap' : ''}">{@html hljs.highlightAuto(info.content).value}<hr /></pre>
            {/if}
        {:else if info.type === "bigtext" }
            <textarea class="file-text" readonly>{bigtextContent || "(empty)"}</textarea>
        {:else if info.type === "image"}
            <div class="content-wrapper" style="text-align: center">
                <img alt={info.path} src={info.content} />
            </div>
        {:else if info.type === "binary"}
            <div class="content-wrapper">
                <InlineNotification
                    lowContrast
                    kind="warning"
                    hideCloseButton>
                    <div>
                        <h6>{info.text}</h6>
                        <p>This is probably a binary file, cannot preview.</p>
                        <p>Copy its path and try to view it on your local machine.</p>
                    </div>
                </InlineNotification>
            </div>
        {:else}
            <div class="content-wrapper">Loading ...</div>
        {/if}
    </div>
</div>

<style>
    .filepreview-wrapper {
        display: grid;
        grid-template-rows: auto 1fr;
        height: 100%;
        overflow: auto;
    }
    .filepreview-actions {
        display: flex;
        flex-direction: row;
        align-items: center;
        column-gap: .5rem;
        padding: 1rem;
        background-color: #e6e6e6;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
    }
    .filepreview-actions :global(button.bx--btn) {
        font-size: .8rem;
    }
    .filepreview-actions :global(button.bx--btn--icon-only.bx--btn--ghost) {
        background: #e4e4e4;
        outline: 1px solid #797979
    }
    .filepreview-actions :global(button.bx--btn--icon-only.bx--btn--selected) {
        background: #6ea5ff;
    }
    .filepreview-content {
        overflow: auto;
    }
    .filepreview-content img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }
    .filepreview-content .content-wrapper {
        height: 100%;
        padding: 1rem;
    }
    .filepreview-content pre hr {
        margin: 0;
        height: 0;
        border: 0;
    }
    .file-text {
        width: 100%;
        height: 100%;
        border: none;
        resize: none;
        background-color: #f4f4f4;
        padding: 1rem;
        font-family: IBM Plex Mono,Menlo,DejaVu Sans Mono,Bitstream Vera Sans Mono,Courier,monospace;
        font-size: 0.9rem;
        margin: -.1rem;
        line-height: 1.2;
    }
    .file-text:focus {
        outline: none;
    }
    .file-text.text-wrap {
        white-space: pre-wrap;
    }
</style>
