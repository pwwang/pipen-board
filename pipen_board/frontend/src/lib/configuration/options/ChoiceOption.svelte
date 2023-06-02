<script>
    import { createEventDispatcher, onMount } from "svelte";
    import Dropdown from "carbon-components-svelte/src/Dropdown/Dropdown.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { validateData } from "../../utils";
    import { removeError, setError } from "../../store";

    export let key;
    export let value;
    export let choices;
    export let choicesDesc;
    export let activeNavItem;
    export let required = false;
    export let readonly = false;

    let button = null;
    let selectedId = choices.indexOf(value);
    let origSelectedId = selectedId;
    let invalid = false;
    let invalidText = "";
    let dispatch = createEventDispatcher();

    const fmtItem = (item) => {
        const desc = choicesDesc ? choicesDesc[item.id] : null;
        return desc ? `${item.text}: ${desc}` : item.text;
    };

    const validateValue = (sid) => {
        if (sid !== -1 || !required) {
            invalid = false;
            return;
        }

        const error = validateData(undefined, ["required"]);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setError(`${activeNavItem} / ${key}`, invalidText);
        } else {
            removeError(`${activeNavItem} / ${key}`);
        }
    };

    // Change the value and pass it to the parent component
    $: value = choices[selectedId];

    onMount(() => {
        button.onfocus = () => {
            dispatch("focus");
        };
        button.onblur = () => {
            dispatch("blur");
        };

        validateValue(selectedId);
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
            {invalid}
            {invalidText}
            label="Select an option"
            bind:selectedId
            bind:ref={button}
            on:select={e => {
                if (readonly)  {selectedId = origSelectedId;}
            }}
            items={choices.map((choice) => ({
                id: choices.indexOf(choice),
                text: choice,
            }))}
        />
    </div>
</OptionFrame>
