<script>
    import TextInput from "carbon-components-svelte/src/TextInput/TextInput.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import Add from "carbon-icons-svelte/lib/Add.svelte";
    import Subtract from "carbon-icons-svelte/lib/Subtract.svelte";

    export let key;
    export let value;

    let newkey;
    let newvalue;

    if (Array.isArray(value)) {
        if (value.length == 0) {
            value = [[newkey, newvalue]];
        } else if (value.at(-1)[0]) {
            value = [...value, [newkey, newvalue]];
        }
    } else {
        if (value) {
            console.warn(`Option ${key}: value is not an array, but it is not empty. It will be ignore.`)
        }
        value = [[newkey, newvalue]];
    }
</script>

{#each value as v, i (i)}
<form class="morelike-wrapper" on:mouseenter on:mouseleave>
    <div class="morelike-label">
        <TextInput
            on:focus
            on:blur
            size="sm"
            title={v[0] ? v[0] : key}
            placeholder={key}
            bind:value={value[i][0]}
        />
    </div>
    <div class="morelike-equal">=</div>
    <div class="morelike-value">
        <TextInput
            on:focus
            on:blur
            size="sm"
            bind:value={value[i][1]}
        />
    </div>
    <div class="morelike-action">
        {#if i == value.length - 1}
        <Button
            icon={Add}
            size="small"
            kind="tertiary"
            iconDescription="Add a new key-value pair"
            on:click={() => {value = [...value, [newkey, newvalue]]; newkey = null; newvalue = null} }
        />
        {:else}
        <Button
            icon={Subtract}
            size="small"
            kind="danger"
            iconDescription="Delete this key-value pair"
            on:click={() => value = value.filter((_, j) => j != i)}
        />
        {/if}
    </div>
</form>
{/each}

<style>
    .morelike-wrapper {
        display: flex;
        align-items: center;
        gap: 0.2rem;
        justify-content: space-between;
        margin-right: -2.2rem;
    }
    .morelike-label {
        flex: 2;
        max-width: 10rem;
        min-width: 8rem;
    }
    .morelike-label :global(input) {
        width: 100%;
        padding: 0.5rem 0.5rem;
    }
    .morelike-value {
        flex-grow: 2;
    }
</style>
