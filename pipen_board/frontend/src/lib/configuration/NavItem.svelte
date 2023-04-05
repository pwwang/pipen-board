<script>
    import { storedErrors } from "../store";

    export let text;
    export let activeNavItem;
    export let sub = false;
    export let is_start = false;
    // whether the process is hidden for config
    export let hidden = false;

    let errored = false;

    storedErrors.subscribe((errors) => {
        errored = Object.keys(errors).map(e => e.split(" / ")[0]).includes(text);
    });

    $: active = text === activeNavItem;
</script>

<button
    {...$$restProps}
    class="navitem {hidden ? 'hidden' : ''} {active ? 'active' : ''} {sub ? 'sub' : ''} {errored ? 'errored' : ''} {is_start ? 'start-proc' : ''} {$$restProps.class ? $$restProps.class : ''}"
    on:click={() => {activeNavItem = text}}
>
    <span>{text}</span>
</button>

<style>
    button.navitem {
        padding: .6rem 1.2rem;
        cursor: pointer;
        display: block;
        width: 100%;
        border-width: 0;
        background-color: transparent;
        text-align: left;
        position: relative;
        overflow: hidden;
    }
    button.navitem:hover {
        background-color: #e6e6e6;
    }
    button.navitem.active {
        background-color: #e6e6e6;
        font-weight: bold;
    }
    button.navitem.active::after {
        content: '';
        position: absolute;
        right: 0;
        top: 50%;
        display: block;
        border-left: 5px solid #fff;
        border-top: 5px solid #fff;
        width: 25px;
        height: 25px;
        float: right;
        transform: translate(50%, -50%) rotate(-45deg);
    }
    button.navitem.hidden {
        font-style: italic;
        color: #999999;
    }
    button.sub {
        line-height: 0.8;
    }
    button.start-proc > span::after {
        content: "*";
        padding-left: 3px;
        color: #008d00;
        vertical-align: middle;
        font-size: .8rem;
    }
</style>
