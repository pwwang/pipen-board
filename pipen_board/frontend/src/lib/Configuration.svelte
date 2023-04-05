<script>
    import * as itoml from "@iarna/toml";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import Modal from "carbon-components-svelte/src/Modal/Modal.svelte";
    import CodeSnippet from "carbon-components-svelte/src/CodeSnippet/CodeSnippet.svelte";
    import Loading from "carbon-components-svelte/src/Loading/Loading.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import Save from "carbon-icons-svelte/lib/Save.svelte";
    import SaveModel from "carbon-icons-svelte/lib/SaveModel.svelte";
    import Download from "carbon-icons-svelte/lib/Download.svelte";
    import IbmWatsonNaturalLanguageUnderstanding from "carbon-icons-svelte/lib/IbmWatsonNaturalLanguageUnderstanding.svelte";

    import {
        SECTION_PIPELINE_OPTS,
        SECTION_PROCESSES,
        SECTION_PROCGROUPS,
        SECTION_ADDITIONAL_OPTS,
        SECTION_RUNNING_OPTS,
        DEFAULT_DESCRIPTIONS,
    } from "./constants.js";
    import { finalizeConfig, IS_DEV } from "./utils.js";
    import { descFocused, storedErrors } from "./store.js";
    import NavItem from "./configuration/NavItem.svelte";
    import NavDivider from "./configuration/NavDivider.svelte";
    import Description from "./configuration/Description.svelte";
    import GeneralOptions from "./configuration/GeneralOptions.svelte";
    import RunningOptions from "./configuration/RunningOptions.svelte";
    import HiddenOptions from "./configuration/HiddenOptions.svelte";

    export let pipelineName;
    export let pipelineDesc;
    export let configfile;
    export let start = false;
    export let histories;

    let data;
    let error;

    let activeNavItem = SECTION_PIPELINE_OPTS;
    let toml = "";
    let tomlShow = false;
    let saving = false;
    let dragStartX = null;
    let initWidth = null;

    let toastNotify = { kind: undefined, subtitle: undefined };

    let itemDescription;
    $: activeDescription = itemDescription || DEFAULT_DESCRIPTIONS[activeNavItem];

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
        let response = {};
        try {
            response = await fetch("/api/config/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    data: JSON.stringify(data),
                    configfile: configfile && !saveas ? configfile : null,
                }),
            });
        } catch (error) {
            response.statusText = error;
        } finally {
            saving = false;
        }
        if (!response.ok) {
            toastNotify.kind = "error";
            toastNotify.subtitle = `Failed to save: ${response.status} ${response.statusText}`;
        } else {
            const saved = await response.json();
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
        }
    };

    const downloadConfig = function () {
        const element = document.createElement("a");
        // @ts-ignore
        const file = new Blob([itoml.stringify(finalizeConfig(data))], {
            type: "text/plain",
        });
        element.href = URL.createObjectURL(file);
        element.download = "config.toml";
        document.body.appendChild(element);
        element.click();
        element.remove();
    };

    const loadData = async () => {
        let rawdata, schema;
        if (configfile) {
            try {
                const fetched = await fetch("/api/history/get", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ configfile }),
                });
                if (!fetched.ok)
                    throw new Error(`${fetched.status} ${fetched.statusText}`);
                rawdata = await fetched.json();
            } catch (e) {
                error = `<strong>Failed to fetch or parse pipeline data from configuration file:</strong> <br /><br /><pre>${e.stack}</pre>`;
            }
        } else {
            try {
                const fetched = await fetch("/api/config/pipeline");
                if (!fetched.ok)
                    throw new Error(`${fetched.status} ${fetched.statusText}`);
                rawdata = await fetched.json();
            } catch (e) {
                error = `<strong>Failed to fetch or parse pipeline data:</strong> <br /><br /><pre>${e.stack}</pre>`;
            }
        }

        if (!error) {
            try {
                const fetched_schema = await fetch("/assets/schema.json");
                if (!fetched_schema.ok)
                    throw new Error(
                        `${fetched_schema.status} ${fetched_schema.statusText}`
                    );
                schema = await fetched_schema.json();
            } catch (e) {
                error = `<strong>Failed to fetch or parse schema:</strong> <br /><br /><pre>${e.stack}</pre>`;
            }
        }

        if (!error) {
            try {
                const jsschema = await import("@cfworker/json-schema");
                const valid = jsschema.validate(rawdata, schema);
                if (!valid.valid) {
                    throw new Error(
                        valid.errors.map((e) => e.error).join("\n")
                    );
                }
            } catch (e) {
                error = `<strong>Pipeline data is not valid:</strong> <br /><br /><pre>${e.stack}</pre>`;
            }
        }
        if (!error) {
            pipelineName = rawdata[SECTION_PIPELINE_OPTS].name.value;
            pipelineDesc = rawdata[SECTION_PIPELINE_OPTS].desc.value;
            for (const proc in rawdata[SECTION_PROCESSES]) {
                DEFAULT_DESCRIPTIONS[proc] = rawdata[SECTION_PROCESSES][proc].desc;
            }
            if (rawdata[SECTION_PROCGROUPS]) {
                for (const group in rawdata[SECTION_PROCGROUPS]) {
                    DEFAULT_DESCRIPTIONS[
                        `${group} Arguments`
                    ] = `Arguments for process group: ${group}`;
                    for (const proc in rawdata[SECTION_PROCGROUPS][group].PROCESSES) {
                        DEFAULT_DESCRIPTIONS[proc] =
                        rawdata[SECTION_PROCGROUPS][group].PROCESSES[proc].desc;
                    }
                }
            }
            if (rawdata[SECTION_RUNNING_OPTS]) {
                for (const running in rawdata[SECTION_RUNNING_OPTS]) {
                    DEFAULT_DESCRIPTIONS[running] =
                    rawdata[SECTION_RUNNING_OPTS][running].desc;
                }
            }
            if (IS_DEV) {
                // @ts-ignore
                window.data = rawdata;
            }
        }

        return rawdata;
    }

    $: if (start && !data) {
        loadData().then(dat => {data = dat;});
    }
</script>

<svelte:window
    on:mouseup={handleDragEnd}
    on:mousemove={handleDrag} />

{#if error}
    <Modal
        class="model-error"
        passiveModal
        danger
        open={true}
        preventCloseOnClickOutside={true}
        modalHeading="Error"
        on:close={() => {}}
    >
        {@html error}
        <br />
        <Button
            kind="tertiary"
            size="small"
            on:click={() => {
                if (histories.length > 0) {
                    configfile = undefined;
                } else {
                    alert("No history available");
                }
            }}
        >Back to History</Button>
    </Modal>
{:else if !data && start}
<Loading
    class="pipen-cli-config-loading"
    style="--content: 'Loading pipeline data {configfile ? `from ${configfile}` : ''}...'"
    description="Loading pipeline data ..." />
{:else if data && start}
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
                {#each Object.keys(data[SECTION_PROCESSES]) as proc}
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
                    {#if data[SECTION_PROCGROUPS][procgroup].ARGUMENTS}
                        <NavItem
                            sub
                            text="{procgroup} Arguments"
                            bind:activeNavItem
                        />
                    {/if}
                    {#each Object.keys(data[SECTION_PROCGROUPS][procgroup].PROCESSES) as proc}
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
                {#each Object.keys(data[SECTION_RUNNING_OPTS]) as running}
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
                    <GeneralOptions
                        bind:description={itemDescription}
                        bind:data={data[SECTION_PROCESSES][proc].value}
                        {activeNavItem}
                        general_filter={(k) => !k.endsWith("_opts") && k !== "envs" && k !== "in"}
                        title="Process Options"
                    />
                {/if}
            {/each}
            {#if data[SECTION_PROCGROUPS]}
                {#each Object.keys(data[SECTION_PROCGROUPS]) as group}
                    {#if activeNavItem === `${group} Arguments`}
                        {#if data[SECTION_PROCGROUPS][group].ARGUMENTS}
                        <GeneralOptions
                            bind:description={itemDescription}
                            bind:data={data[SECTION_PROCGROUPS][group].ARGUMENTS}
                            {activeNavItem}
                            title="Process Group Arguments"
                        />
                        {/if}
                    {:else}
                        {#each Object.keys(data[SECTION_PROCGROUPS][group].PROCESSES) as proc}
                            {#if proc === activeNavItem}
                                {#if data[SECTION_PROCGROUPS][group].PROCESSES[proc].hidden}
                                <HiddenOptions />
                                {:else}
                                <GeneralOptions
                                    bind:description={itemDescription}
                                    bind:data={data[SECTION_PROCGROUPS][group].PROCESSES[proc].value}
                                    {activeNavItem}
                                    general_filter={(k) => !k.endsWith("_opts") && k !== "envs" && k !== "in"}
                                    title="Process Options"
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
                            bind:description={itemDescription}
                            bind:data={data[SECTION_RUNNING_OPTS][running]}
                            {activeNavItem}
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
                    on:click={generateTOML}>Generate TOML Configuration</Button
                >
                <span class="separator"></span>
                <Button
                    icon={Save}
                    size="small"
                    disabled={saving}
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
                {#if configfile}
                Loaded from <i>{configfile}</i>
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
</style>
