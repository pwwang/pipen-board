<script>
    import { createEventDispatcher, onMount } from "svelte";
    import Dropdown from "carbon-components-svelte/src/Dropdown/Dropdown.svelte";
    import OptionFrame from "./OptionFrame.svelte";

    export let key;
    export let value;
    export let choices;
    export let choicesDesc;
    export let readonly = false;

    let button = null;
    let selectedId = choices.indexOf(value);
    let origSelectedId = selectedId;
    let dispatch = createEventDispatcher();

    const fmtItem = (item) => {
        const desc = choicesDesc ? choicesDesc[item.id] : null;
        return desc ? `${item.text}: ${desc}` : item.text;
    };

    $: value = choices[selectedId];

    onMount(() => {
        button.onfocus = () => {
            dispatch("focus");
        };
        button.onblur = () => {
            dispatch("blur");
        };
    });
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div slot="label">{key} {readonly ? '(readonly)' : ''}</div>
    <div slot="field">
        <Dropdown
            itemToString={fmtItem}
            size="sm"
            titleText={key}
            hideLabel
            bind:selectedId
            bind:ref={button}
            on:select={e => { if (readonly) selectedId = origSelectedId; }}
            items={choices.map((choice) => ({
                id: choices.indexOf(choice),
                text: choice,
            }))}
        />
    </div>
</OptionFrame>
