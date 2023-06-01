<script>
    import * as itoml from "@iarna/toml";
    import Accordion from "carbon-components-svelte/src/Accordion/Accordion.svelte";
    import AccordionItem from "carbon-components-svelte/src/Accordion/AccordionItem.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import TextArea from "carbon-components-svelte/src/TextArea/TextArea.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import Checkbox from "carbon-components-svelte/src/Checkbox/Checkbox.svelte";
    import TooltipDefinition from "carbon-components-svelte/src/TooltipDefinition/TooltipDefinition.svelte";
    import Modal from "carbon-components-svelte/src/Modal/Modal.svelte";
    import ChevronUp from "carbon-icons-svelte/lib/ChevronUp.svelte";
    import ChevronDown from "carbon-icons-svelte/lib/ChevronDown.svelte";
    import ContinueFilled from "carbon-icons-svelte/lib/ContinueFilled.svelte";
    import Option from "./options/Option.svelte";
    import { hasHidden, getKeysHidden, getKeysUnhidden, autoHeight, finalizeConfig, fetchAPI } from "../utils";
    import { storedErrors } from "../store";

    export let data;
    // used to generate toml
    export let config_data;
    export let description;
    export let initDescription = undefined;
    export let activeNavItem;
    export let isRunning;
    export let openConfirm = false;

    if (initDescription) {
        description = initDescription;
    }

    let invalid = false;
    let invalidText = "No command generated or filled."

    let showHiddens = {};
    let generatedCommand = '';
    let toastNotify = { kind: undefined, subtitle: undefined, timeout: 3000 };
    let errors = {};
    let submitting = false;
    let overwriteConfig = false;

    $: tomlfile = data.value[data.configfile].value;
    $: {
        data = data;
        generateCommand();
    }

    const setError = (key, value) => {
        errors[key] = value;
    }
    const removeError = (key) => {
        delete errors[key];
    }

    const checkErrors = function(es) {
        if (Object.keys(es).length === 0) {
            return false;
        }
        const errkeys = Object.keys(es);
        toastNotify.kind = "error";
        toastNotify.subtitle = `
            There are errors in the configuration. Please fix them before generating the command:
            <br />
            <ul>
                ${errkeys.map(k => `<li>${k}: ${es[k]}</li>`).join("")}
            </ul>
        `;
        return true;
    }

    const runCommandConfirm = async () => {
        if (/^\s*$/.test(generatedCommand)) {
            invalid = true;
            return;
        }
        openConfirm = true;
    };

    const runCommand = async () => {
        openConfirm = false;
        submitting = true;

        try {
            const response = await fetchAPI("/api/run", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    command: generatedCommand,
                    // @ts-ignore
                    config: itoml.stringify(finalizeConfig(config_data)),
                    overwriteConfig,
                    tomlfile,
                }),
            });
            if (!response.ok) {
                throw new Error(`Failed to run command: ${response.msg}`);
            } else {
                isRunning = isRunning + 1;
            }
        } catch (error) {
            toastNotify.kind = "error";
            toastNotify.subtitle = error;
            toastNotify.timeout = 0;
            return;
        } finally {
            submitting = false;
        }
    }

    const generateCommand = () => {
        if (checkErrors($storedErrors)) {
            return;
        }
        if (checkErrors(errors)) {
            return;
        }

        let obj = {};
        for (let key in data.value) {
            obj[key] = data.value[key].value;
        }
        generatedCommand = data.command.replace(/\$\{(\w+)\}/g, (_, key) => obj[key]);
        invalid = false;
    }
</script>

<Modal
  size="sm"
  bind:open={openConfirm}
  modalHeading="Running pipeline"
  primaryButtonText="Confirm"
  secondaryButtonText="Cancel"
  preventCloseOnClickOutside={true}
  class="running-confirm-modal"
  on:click:button--secondary={() => {openConfirm = false}}
  on:click:button--primary={runCommand}
>
  <p>Are you sure to run the command?</p>
  <p>&nbsp;</p>
  <p><code>{generatedCommand}</code></p>
  <p>&nbsp;</p>
  <p>This will override the "Running"/"Previous Run" tab.</p>
  <p>&nbsp;</p>
  <p>You can also save the configuration into <code>{tomlfile}</code> using the <code>Generate TOML Configuration</code> button on the left bottom, and run the command manually in your teminal.</p>
</Modal>

<Accordion align="start">
    <AccordionItem open title="Options">
        {#each getKeysUnhidden(data.value, activeNavItem) as key}
            <Option {key} {activeNavItem} {setError} {removeError} bind:data={data.value[key]} bind:description />
        {/each}
        {#if showHiddens.general}
            {#each getKeysHidden(data, activeNavItem) as key}
                <Option {key} {activeNavItem} {setError} {removeError} bind:data={data.value[key]} bind:description />
            {/each}
        {/if}
        {#if hasHidden(data.value, activeNavItem)}
            <Button
                class="show-hidden"
                size="small"
                kind="ghost"
                icon={showHiddens.general ? ChevronUp : ChevronDown}
                on:click={() => {showHiddens.general = !showHiddens.general} }>
                {showHiddens.general ? 'Less' : 'More'}
            </Button>
        {/if}
    </AccordionItem>
    <AccordionItem open class="accordion-less-padding-right" title="Generated Command">
        <TextArea
            {invalid}
            {invalidText}
            readonly={!data.editable}
            bind:value={generatedCommand}
            on:input={e => autoHeight(e.target)} />
        <div class="running-action-wrapper">
            {#if data.allow_run}
            <TooltipDefinition
                direction="bottom"
                align="center"
                tooltipText="Save the configurations to {tomlfile} and run the generated command.">
                <Button
                    size="small"
                    kind="tertiary"
                    icon={ContinueFilled}
                    disabled={submitting || generatedCommand === ""}
                    iconDescription="Run the Command"
                    on:click={runCommandConfirm}>
                    Run the Command
                </Button>
            </TooltipDefinition>
            <Checkbox bind:checked={overwriteConfig} labelText="Overwrite {tomlfile}" />
            {/if}
        </div>

    </AccordionItem>
</Accordion>

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
    div.running-action-wrapper {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 1rem;
        flex-wrap: wrap;
    }
</style>