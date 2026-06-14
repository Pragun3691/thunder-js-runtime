let base = {
    name: "Pragun",
    settings: {
        theme: "dark"
    },
    score: 10
};

let override = {
    score: 25,
    active: true
};

let result = {
    id: 1,
    ...base,
    ...override,
    name: "Final"
};

result.settings.theme = "light";

console.log(result.id);
console.log(result.name);
console.log(result.score);
console.log(result.active);
console.log(base.score);
console.log(base.name);
console.log(base.settings.theme);