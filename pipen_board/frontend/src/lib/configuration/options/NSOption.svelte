<script>
    import NonNSOption from './NonNSOption.svelte';
    import OptionFrame from './OptionFrame.svelte';
    import { parseMarkdown } from '../../utils.js';

    export let key;
    export let value;
    export let desc;
    // the description bound to the parent
    export let description;
    export let activeNavItem;
    export let level = 0;
    export let readonly = false;
    export let setError;
    export let removeError;

</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div slot="label" class={readonly ? "readonly-label" : ""}>{key}</div>
    <div slot="field" class="ns-desc">{@html parseMarkdown(desc)}</div>
</OptionFrame>

<div class="ns-wrapper" style="--level:{level};">
{#each Object.keys(value).sort((a, b) => (value[a].order || 0) - (value[b].order || 0)) as k}
    {#if value[k].type === 'ns' || value[k].type === 'namespace'}
        <svelte:self
            key={k}
            desc={value[k].desc}
            level={level + 1}
            readonly={readonly || value[k].readonly}
            bind:description
            {activeNavItem}
            {setError}
            {removeError}
            bind:value={value[k].value}
        />
    {:else}
        <NonNSOption
            key={k}
            {setError}
            {removeError}
            {activeNavItem}
            readonly={readonly || value[k].readonly}
            bind:data={value[k]}
            bind:description
        />
    {/if}
{/each}
</div>

<style>
.ns-wrapper {
    border-left: 5px solid rgb(180, 180, 180);
    padding: .2rem .2rem .2rem 1rem;
    background-color: rgba(120, 120, 120, calc((var(--level) + 1) * 0.1));
}
</style>