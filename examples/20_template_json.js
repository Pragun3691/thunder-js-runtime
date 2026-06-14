let name = "Pragun";
let score = 42;

console.log(`Hello ${name}`);
console.log(`${name} scored ${score}`);
console.log(`Result: ${score >= 40 ? "pass" : "fail"}`);

let user = {
    name: "Pragun",
    score: 42,
    missing: undefined,
    fn: function() {}
};

console.log(JSON.stringify(user));
console.log(JSON.stringify([1, undefined, NaN, Infinity]));
console.log(`JSON: ${JSON.stringify({ active: true })}`);
