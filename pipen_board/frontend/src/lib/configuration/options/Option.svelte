<script>
    import NSOption from "./NSOption.svelte";
    import NonNsOption from "./NonNSOption.svelte";

    export let key;
    // type, desc, value, ...
    export let data;
    // bound description
    export let description;
    export let activeNavItem;
    export let storeError = true;
</script>

{#if data.type === 'ns' || data.type === 'namespace'}
<NSOption
    {key}
    desc={data.desc}
    {activeNavItem}
    {storeError}
    readonly={data.readonly}
    bind:description
    bind:value={data.value}
    />
{:else}
<NonNsOption
    bind:data
    bind:description
    {key}
    {activeNavItem}
    {storeError}
    />
{/if}
