<script>
    import Accordion from "carbon-components-svelte/src/Accordion/Accordion.svelte";
    import AccordionItem from "carbon-components-svelte/src/Accordion/AccordionItem.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import TextArea from "carbon-components-svelte/src/TextArea/TextArea.svelte";
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

    const generateCommand = () => {
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
            <Option {key} {activeNavItem} storeError={false} bind:data={data.value[key]} bind:description />
        {/each}
        {#if showHiddens.general}
            {#each getKeysHidden(data, activeNavItem) as key}
                <Option {key} {activeNavItem} storeError={false} bind:data={data.value[key]} bind:description />
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
        <Button
            size="small"
            kind="tertiary"
            icon={Cicsplex}
            iconDescription="Generate Command based on the options"
            on:click={generateCommand}>
            Generate Command
        </Button>
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
