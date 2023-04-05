<script>
    import Accordion from "carbon-components-svelte/src/Accordion/Accordion.svelte";
    import AccordionItem from "carbon-components-svelte/src/Accordion/AccordionItem.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import { hasHidden, getKeysHidden, getKeysUnhidden } from "../utils";
    import ChevronUp from "carbon-icons-svelte/lib/ChevronUp.svelte";
    import ChevronDown from "carbon-icons-svelte/lib/ChevronDown.svelte";
    import Option from "./options/Option.svelte";

    export let title = "General Options";
    export let data;
    export let description;
    export let general_filter = (x) => true;
    export let activeNavItem;

    let showHiddens = {};
</script>

<Accordion align="start">
    <AccordionItem open title={title}>
        {#each getKeysUnhidden(data, activeNavItem).filter(general_filter) as key}
            <Option {key} {activeNavItem} bind:data={data[key]} bind:description />
        {/each}
        {#if showHiddens.general}
            {#each getKeysHidden(data, activeNavItem).filter(general_filter) as key}
                <Option {key} {activeNavItem} bind:data={data[key]} bind:description />
            {/each}
        {/if}
        {#if hasHidden(data, activeNavItem)}
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
    {#each Object.keys(data).filter((k) => !general_filter(k)) as key}
        <AccordionItem open title="{key}: {data[key].desc}">
            {#each getKeysUnhidden(data[key].value, `${activeNavItem}/${key}`) as k}
                <Option {activeNavItem} key={k} bind:data={data[key].value[k]} bind:description />
            {/each}
            {#if showHiddens[key]}
                {#each getKeysHidden(data[key].value, `${activeNavItem}/${key}`) as k}
                    <Option {activeNavItem} key={k} bind:data={data[key].value[k]} bind:description />
                {/each}
            {/if}
            {#if hasHidden(data[key].value, `${activeNavItem}/${key}`)}
                <Button
                    class="show-hidden"
                    size="small"
                    kind="ghost"
                    icon={showHiddens[key] ? ChevronUp : ChevronDown}
                    on:click={() => {showHiddens[key] = !showHiddens[key]} }>
                    {showHiddens[key] ? 'Less' : 'More'}
                </Button>
            {/if}
        </AccordionItem>
    {/each}
</Accordion>
