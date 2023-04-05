import { writable } from "svelte/store";

export const storedErrors = writable({});
export const storedConfigfile = writable(
    localStorage.getItem("configfile") || ""
);
export const descFocused = writable(false);

export const setError = (key, error) => {
    storedErrors.update((errors) => {
        return { ...errors, [key]: error };
    });
};

export const removeError = (key) => {
    storedErrors.update((errors) => {
        // @ts-ignore
        const { [key]: _, ...rest } = errors;
        return rest;
    });
};

export const updateErrors = (errors) => {
    storedErrors.set(errors);
}

export const updateConfigfile = (configfile) => {
    storedConfigfile.set(configfile);
}

storedConfigfile.subscribe((configfile) => {
    localStorage.setItem("configfile", configfile);
});
