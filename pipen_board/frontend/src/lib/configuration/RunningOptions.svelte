<script>
    import Accordion from "carbon-components-svelte/src/Accordion/Accordion.svelte";
    import AccordionItem from "carbon-components-svelte/src/Accordion/AccordionItem.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import TextArea from "carbon-components-svelte/src/TextArea/TextArea.svelte";
    import ToastNotification from "carbon-components-svelte/src/Notification/ToastNotification.svelte";
    import TooltipDefinition from "carbon-components-svelte/src/TooltipDefinition/TooltipDefinition.svelte";
    import ChevronUp from "carbon-icons-svelte/lib/ChevronUp.svelte";
    import ChevronDown from "carbon-icons-svelte/lib/ChevronDown.svelte";
    import Cicsplex from "carbon-icons-svelte/lib/Cicsplex.svelte";
    import ContinueFilled from "carbon-icons-svelte/lib/ContinueFilled.svelte";
    import Option from "./options/Option.svelte";
    import { hasHidden, getKeysHidden, getKeysUnhidden, autoHeight } from "../utils";

    export let data;
    export let description;
    export let activeNavItem;

    let invalid = false;
    let invalidText = "No command generated."

    let showHiddens = {};
    let generatedCommand = '';
    let toastNotify = { kind: undefined, subtitle: undefined };
    let errors = {};

    const setError = (key, value) => {
        errors[key] = value;
    }
    const removeError = (key) => {
        delete errors[key];
    }

    const generateCommand = () => {
        if (Object.keys(errors).length > 0) {
            const errkeys = Object.keys(errors);
            toastNotify.kind = "error";
            toastNotify.subtitle = `
                There are errors in the configuration. Please fix them before generating the command:
                <br />
                <ul>
                    ${errkeys.map(k => `<li>${k}: ${errors[k]}</li>`).join("")}
                </ul>
            `;
            return;
        }
        let obj = {};
        for (let key in data.value) {
            obj[key] = data.value[key].value;
        }
        generatedCommand = data.command.replace(/\$\{(\w+)\}/g, (_, key) => obj[key]);
        invalid = false;
    }

    const runCommand = () => {
        if (/^\s*$/.test(generatedCommand)) {
            invalid = true;
            return;
        }
    }

</script>

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
            value={generatedCommand}
            on:input={e => autoHeight(e.target)} />
        <br />
        <TooltipDefinition
            direction="bottom"
            align="center"
            tooltipText="Save the configurations to '<{data.configfile}>' and generate command for running the pipeline.">
            <Button
                size="small"
                kind="tertiary"
                icon={Cicsplex}
                iconDescription="Generate Command based on the options"
                on:click={generateCommand}>
                Generate Command
            </Button>
        </TooltipDefinition>
        <Button
            size="small"
            kind="danger-tertiary"
            icon={ContinueFilled}
            iconDescription="Run the Command"
            on:click={runCommand}>
            Run the Command
        </Button>
    </AccordionItem>
</Accordion>

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