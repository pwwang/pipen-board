<script>
    export let group = null;
</script>

{#if group === null}
<hr class="whole" />
{:else}
<div><hr class="first" /><span>{group}</span><hr class="last" /></div>
{/if}

<style>
    hr.whole {
        border: 0;
        border-top: 1px solid #e6e6e6;
        width: 18rem;
    }

    div {
        display: flex;
        align-items: center;
        padding: 1rem 1.2rem 0.2rem 1.2rem;
        gap: 1rem;
    }
    div > span {
        font-size: small;
        color: #6f6f6f;
    }
    div > hr {
        border: 0;
        border-top: 1px solid #e6e6e6;
    }
    div > hr.first {
        width: .8rem;
    }
    div > hr.last {
        flex-grow: 1;
    }
</style>
