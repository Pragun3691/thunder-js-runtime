let counter = {
    value: 0,
    increment: function() {
        this.value++;
        return this.value;
    }
};

console.log(counter.increment());
console.log(counter.increment());
console.log(counter.value);

let user = {
    name: "Pragun",
    greet: function() {
        return "Hello " + this.name;
    }
};

console.log(user.greet());
console.log(user?.greet?.());
console.log(user?.profile?.name);

let missing = null;
console.log(missing?.name);
console.log(missing?.method?.());

console.log(null ?? "fallback");
console.log(undefined ?? "fallback");
console.log(0 ?? 10);
console.log(false ?? true);
console.log("" ?? "text");
console.log((null ?? false) || true);
