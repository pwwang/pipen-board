<script>
    // Used by Layout.svelte
    import * as itoml from "@iarna/toml";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import Link from "carbon-components-svelte/src/Link/Link.svelte";
    import Modal from "carbon-components-svelte/src/Modal/Modal.svelte";
    import CodeSnippet from "carbon-components-svelte/src/CodeSnippet/CodeSnippet.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import Save from "carbon-icons-svelte/lib/Save.svelte";
    import SaveModel from "carbon-icons-svelte/lib/SaveModel.svelte";
    import Download from "carbon-icons-svelte/lib/Download.svelte";
    import IbmWatsonNaturalLanguageUnderstanding from "carbon-icons-svelte/lib/IbmWatsonNaturalLanguageUnderstanding.svelte";
    import { storedGlobalChanged } from "./store.js";

    import {
        SECTION_PIPELINE_OPTS,
        SECTION_PROCESSES,
        SECTION_PROCGROUPS,
        SECTION_ADDITIONAL_OPTS,
        SECTION_RUNNING_OPTS,
        DEFAULT_DESCRIPTIONS,
    } from "./constants.js";
    import { finalizeConfig, fetchAPI } from "./utils.js";
    import { descFocused, storedErrors } from "./store.js";
    import NavItem from "./configuration/NavItem.svelte";
    import NavDivider from "./configuration/NavDivider.svelte";
    import Description from "./configuration/Description.svelte";
    import GeneralOptions from "./configuration/GeneralOptions.svelte";
    import RunningOptions from "./configuration/RunningOptions.svelte";
    import HiddenOptions from "./configuration/HiddenOptions.svelte";

    export let pipelineDesc;
    export let configfile;
    export let histories;
    export let runStarted;
    export let finished;
    export let data;

    let activeNavItem = SECTION_PIPELINE_OPTS;
    let toml = "";
    let tomlShow = false;
    let saving = false;
    let dragStartX = null;
    let initWidth = null;

    let toastNotify = { kind: undefined, subtitle: undefined, timeout: 3000 };

    let itemDescription;

    $: activeDescription = itemDescription || DEFAULT_DESCRIPTIONS[activeNavItem];
    $: pipelineDesc = data[SECTION_PIPELINE_OPTS].desc.value;

    const handleDragStart = function (e) {
        dragStartX = e.clientX;
        initWidth = e.target.nextElementSibling.clientWidth;
    };

    const handleDrag = function (e) {
        if (dragStartX === null) {
            return;
        }
        e.stopPropagation();
        e.preventDefault();
        const dx = e.clientX - dragStartX;
        const width = initWidth - dx < 0 ? 0 : initWidth - dx;
        document.getElementById("container").style.setProperty("--desc-width", `${width}px`);
        // requestAnimationFrame(() => handleDrag(e));
    };

    const handleDragEnd = function () {
        dragStartX = null;
    };

    const generateTOML = function () {
        if (Object.keys($storedErrors).length > 0) {
            const errkeys = Object.keys($storedErrors);
            toastNotify.kind = "error";
            toastNotify.subtitle = `
                There are errors in the configuration. Please fix them before generating TOML configuration:
                <br />
                <ul>
                    ${errkeys.map(k => `<li>${k}: ${$storedErrors[k]}</li>`).join("")}
                </ul>
            `;
            return;
        }
        // generate TOML
        tomlShow = true;
        // @ts-ignore
        toml = itoml.stringify(finalizeConfig(data));
    };

    const saveConfig = async function (saveas = false) {
        if (!$storedGlobalChanged) {
            return;
        }
        if (Object.keys($storedErrors).length > 0) {
            const errkeys = Object.keys($storedErrors);
            toastNotify.kind = "error";
            toastNotify.subtitle = `
                There are errors in the configuration. Please fix them before saving:
                <br />
                <ul>
                    ${errkeys.map(k => `<li>${k}: ${$storedErrors[k]}</li>`).join("")}
                </ul>
            `;
            return;
        }
        saving = true;
        toastNotify.kind = "info";
        toastNotify.subtitle = "Saving data ...";

        let new_name = data.PIPELINE_OPTIONS.name.value;
        let saved;
        if (saveas) {
            if (runStarted && !finished) {
                saving = false;
                toastNotify.kind = "error";
                toastNotify.subtitle = "Pipeline is running. Please stop it or wait it to finish before saving as a new configuration.";
                return;
            }
            new_name = prompt("Please enter a new name for the configuration:");
            if (new_name === null || new_name === "") {
                saving = false;
                toastNotify.kind = "error";
                toastNotify.subtitle = "Failed to save as: no name provided";
                return;
            }
        }
        try {
            saved = await fetchAPI("/api/config/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    data: JSON.stringify(data, null, 4),
                    configfile: configfile && !saveas ? configfile : `new:${new_name}`,
                }),
            });
            if (saved.error) {
                throw new Error(saved.error);
            }
        } catch (error) {
            toastNotify.kind = "error";
            toastNotify.subtitle = `Failed to save: ${error}`;
        } finally {
            saving = false;
        }
        if (toastNotify.kind !== "error") {
            configfile = saved.configfile;
            toastNotify.kind = "success";
            toastNotify.subtitle = `Saved to ${configfile}`;
            const existedHistory = histories.find(h => h.configfile === configfile);
            if (existedHistory) {
                histories = [
                    ...histories.filter(h => h.configfile !== configfile),
                    {...existedHistory, ...saved}
                ]
            } else {
                histories = [...histories, saved];
            }
            storedGlobalChanged.set(false);
        }
    };

    const downloadConfig = function () {
        const element = document.createElement("a");
        // @ts-ignore
        const file = new Blob([toml], { type: "text/plain" });
        element.href = URL.createObjectURL(file);
        element.download = `${data[SECTION_PIPELINE_OPTS].name.value}config.toml`;
        document.body.appendChild(element);
        element.click();
        element.remove();
    };

    const downloadSchema = function () {
        const schema = JSON.stringify(data, null, 4);
        const element = document.createElement("a");
        // @ts-ignore
        const file = new Blob([schema], { type: "text/json" });
        element.href = URL.createObjectURL(file);
        element.download = `${data[SECTION_PIPELINE_OPTS].name.value}.schema.json`;
        document.body.appendChild(element);
        element.click();
        element.remove();
    }

    const shortenConfigfile = (cfile) => {
        // shorten configfile name shown in the footer
        // from
        // example-example-py-examplepipeline.Ex2.L2hvbWUvcHd3YW5nL2dpdGh1Yi9waXBlbi1ib2FyZC8ucGlwZW4.json
        // to
        // example-example-py-examplepipeline.Ex2.L2hvbW...json
        const parts = cfile.split(".");
        const shortened = parts.at(-2).substring(0, 6) + '..';
        parts.splice(-2, 1, shortened);
        return parts.join(".");
    };
</script>

<svelte:window
    on:mouseup={handleDragEnd}
    on:mousemove={handleDrag} />

<Modal passiveModal bind:open={tomlShow} modalHeading="TOML Configuration" preventCloseOnClickOutside>
    <div class="snippet-wrapper">
        <CodeSnippet type="multi" code={toml} />
        <Button icon={Download} size="small" on:click={downloadConfig}
            >Download</Button
        >
    </div>
</Modal>
<div class="container" id="container">
    <aside class="left">
        <NavItem text={SECTION_PIPELINE_OPTS} bind:activeNavItem />

        {#if data[SECTION_ADDITIONAL_OPTS]}
            <NavItem text={SECTION_ADDITIONAL_OPTS} bind:activeNavItem />
        {/if}
        {#if data[SECTION_PROCESSES] && Object.keys(data[SECTION_PROCESSES]).length > 0}
            <NavDivider group="processes" />
            {#each Object.keys(data[SECTION_PROCESSES]).sort((a, b) => data[SECTION_PROCESSES][a].order - data[SECTION_PROCESSES][b].order) as proc}
                <NavItem
                    text={proc}
                    hidden={data[SECTION_PROCESSES][proc].hidden}
                    is_start={data[SECTION_PROCESSES][proc].is_start}
                    sub
                    bind:activeNavItem />
            {/each}
        {/if}
        {#if data[SECTION_PROCGROUPS]}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as procgroup}
                <NavDivider group="group: {procgroup}" />
                <NavItem
                    sub
                    text="{procgroup} Arguments"
                    bind:activeNavItem
                />
                {#each Object.keys(data[SECTION_PROCGROUPS][procgroup].PROCESSES).sort((a, b) => data[SECTION_PROCGROUPS][procgroup].PROCESSES[a].order - data[SECTION_PROCGROUPS][procgroup].PROCESSES[b].order) as proc}
                    <NavItem
                        sub
                        text={proc}
                        hidden={data[SECTION_PROCGROUPS][procgroup].PROCESSES[proc].hidden}
                        is_start={data[SECTION_PROCGROUPS][procgroup].PROCESSES[proc].is_start}
                        bind:activeNavItem />
                {/each}
            {/each}
        {/if}
        {#if data[SECTION_RUNNING_OPTS]}
            <NavDivider group="running options" />
            {#each Object.keys(data[SECTION_RUNNING_OPTS]).sort(
                (a, b) => (data[SECTION_RUNNING_OPTS][a].order || 0) - (data[SECTION_RUNNING_OPTS][b].order || 0)
            ) as running}
                <NavItem sub text={running} bind:activeNavItem />
            {/each}
        {/if}
    </aside>
    <main>
        {#if activeNavItem === SECTION_PIPELINE_OPTS}
            <GeneralOptions
                bind:description={itemDescription}
                bind:data={data[SECTION_PIPELINE_OPTS]}
                {activeNavItem}
                general_filter={(k) => !k.endsWith("_opts")}
            />
        {/if}
        {#if activeNavItem === SECTION_ADDITIONAL_OPTS}
            <GeneralOptions
                bind:description={itemDescription}
                bind:data={data[SECTION_ADDITIONAL_OPTS]}
                title="Additional Options For the Pipeline"
                {activeNavItem}
            />
        {/if}
        {#each Object.keys(data[SECTION_PROCESSES]) as proc}
            {#if proc === activeNavItem}
                {#if data[SECTION_PROCESSES][proc].hidden}
                <HiddenOptions
                    bind:description={itemDescription}
                    initDescription={data[SECTION_PROCESSES][proc].desc} />
                {:else}
                <GeneralOptions
                    bind:description={itemDescription}
                    bind:data={data[SECTION_PROCESSES][proc].value}
                    initDescription={data[SECTION_PROCESSES][proc].desc}
                    {activeNavItem}
                    general_filter={(k) => !k.endsWith("_opts") && k !== "envs" && k !== "in"}
                    title="Process Options"
                />
                {/if}
            {/if}
        {/each}
        {#if data[SECTION_PROCGROUPS]}
            {#each Object.keys(data[SECTION_PROCGROUPS]) as group}
                {#if activeNavItem === `${group} Arguments`}
                    <GeneralOptions
                        bind:description={itemDescription}
                        bind:data={data[SECTION_PROCGROUPS][group].ARGUMENTS}
                        initDescription={data[SECTION_PROCGROUPS][group].desc}
                        {activeNavItem}
                        title="Process Group Arguments"
                    />
                {:else}
                    {#each Object.keys(data[SECTION_PROCGROUPS][group].PROCESSES) as proc}
                        {#if proc === activeNavItem}
                            {#if data[SECTION_PROCGROUPS][group].PROCESSES[proc].hidden}
                            <HiddenOptions
                                bind:description={itemDescription}
                                initDescription={data[SECTION_PROCGROUPS][group].PROCESSES[proc].desc} />
                            {:else}
                            <GeneralOptions
                                bind:description={itemDescription}
                                bind:data={data[SECTION_PROCGROUPS][group].PROCESSES[proc].value}
                                initDescription={data[SECTION_PROCGROUPS][group].PROCESSES[proc].desc}
                                {activeNavItem}
                                general_filter={(k) => !k.endsWith("_opts") && k !== "envs" && k !== "in"}
                                title="Process Options"
                                pgargs={data[SECTION_PROCGROUPS][group].ARGUMENTS}
                            />
                            {/if}
                        {/if}
                    {/each}
                {/if}
            {/each}
        {/if}
        {#if data[SECTION_RUNNING_OPTS]}
            {#each Object.keys(data[SECTION_RUNNING_OPTS]) as running}
                {#if running === activeNavItem}
                    <RunningOptions
                        config_data={data}
                        bind:runStarted
                        bind:description={itemDescription}
                        initDescription={data[SECTION_RUNNING_OPTS][running].desc}
                        bind:data={data[SECTION_RUNNING_OPTS][running]}
                        {activeNavItem}
                        {saveConfig}
                    />
                {/if}
            {/each}
        {/if}
    </main>
    <div class="actions">
        <div class="actions-left">
            <Button
                icon={IbmWatsonNaturalLanguageUnderstanding}
                size="small"
                on:click={generateTOML}>Generate Configuration</Button
            >
            <span class="separator"></span>
            <Button
                icon={Save}
                size="small"
                disabled={saving || !$storedGlobalChanged}
                kind="secondary"
                on:click={e => saveConfig()}>Save</Button
            >
            {#if configfile}
            <Button
                icon={SaveModel}
                size="small"
                disabled={saving}
                kind="secondary"
                on:click={e => saveConfig(true)}>Save As</Button
            >
            {/if}
        </div>
        <div class="actions-right">
            {#if configfile && !configfile.startsWith("new:")}
            Loaded from <Link class="configfile-link" title="Download the schema file" on:click={downloadSchema}>{shortenConfigfile(configfile)}</Link>
            {/if}
        </div>
    </div>
    <div
        class="draggable"
        on:mousedown={handleDragStart}
        ></div>
    <aside
        class="right"
        on:mouseenter={e => descFocused.set(true)}
        on:mouseleave={e => descFocused.set(false)}
        >
        <Description description={activeDescription} />
    </aside>
</div>

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
    div.container {
        --desc-width: 42rem;
        height: 100%;
        display: grid;
        grid-template-columns: 20rem auto .5rem var(--desc-width);
        grid-template-rows: auto 4rem;
        grid-template-areas:
            "laside main draggable raside"
            "actions actions actions actions";
    }
    @media (max-width: 1600px) {
        div.container {
            --desc-width: 32rem;
        }
    }
    @media (max-width: 1200px) {
        div.container {
            --desc-width: 22rem;
        }
    }
    div.actions {
        grid-area: actions;
        background-color: #e4e4e4;
        padding: 1rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    main {
        grid-area: main;
        grid-auto-flow: column;
        padding: 2rem;
        background-color: #e6e6e6;
        overflow: auto;
    }
    aside.left {
        grid-area: laside;
        grid-auto-flow: column;
        padding: 2rem 0;
        background-color: #f4f4f4;
        overflow: auto;
    }
    aside.right {
        grid-area: raside;
        grid-auto-flow: column;
        padding: 2rem;
        background-color: #f7f7f7;
        overflow: auto;
    }
    div.snippet-wrapper :global(.bx--snippet) {
        background-color: #e4e4e4;
        width: 95%;
        max-width: none;
    }
    div.snippet-wrapper :global(.bx--snippet:not(.bx--snippet--expand) > div) {
        max-height: 30rem !important;
    }
    div.actions-left {
        white-space: nowrap;
    }
    div.actions-right {
        text-align: right;
        white-space: break-spaces;
        word-wrap: break-word;
        font-size: .8rem;
    }
    span.separator {
        display: inline-block;
        width: 1rem;
    }
    :global(.configfile-link) {
        font-style: italic;
        cursor: pointer;
    }
</style>
