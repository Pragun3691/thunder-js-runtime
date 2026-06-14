let counter = {
    value: 5,

    add(amount = 1) {
        this.value += amount;
        return this.value;
    }
};

console.log(counter.add());
console.log(counter.add(4));

console.log(0xFF);
console.log(0b1010);
console.log(0o17);
console.log(1.5e2);
console.log(2e-3);

let parsed = JSON.parse('{"name":"Pragun","scores":[10,20],"active":true}');
console.log(parsed.name);
console.log(parsed.scores);
console.log(parsed.active);
console.log(JSON.stringify(JSON.parse('{"x":1,"y":[2,3]}')));

let text = "  hello  ";

console.log("ABC".charAt(1));
console.log("ABC".charCodeAt(1));
console.log("ha".repeat(3));
console.log("7".padStart(3, "0"));
console.log("7".padEnd(3, "0"));
console.log(text.trimStart());
console.log(text.trimEnd());
console.log("hello".at(-1));
console.log("A".concat("B", 3));

console.log(Math.log(1));
console.log(Math.log2(8));
console.log(Math.log10(1000));
console.log(Math.sign(-12));
console.log(Math.hypot(3, 4));
console.log(Math.cbrt(-27));
