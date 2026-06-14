let score = 72;
console.log(score >= 50 ? "pass" : "fail");

let x = 0;
console.log(x > 0 ? "positive" : x < 0 ? "negative" : "zero");

console.log(typeof undefined);
console.log(typeof null);
console.log(typeof true);
console.log(typeof 42);
console.log(typeof "hello");
console.log(typeof function() {});
console.log(typeof []);
console.log(typeof {});
console.log(typeof missingName);

let name = "Pragun";
let age = 20;
let user = { name, age };
console.log(user.name);
console.log(user.age);

function greet(person = "World") {
    return "Hello " + person;
}

const add = (a = 1, b = a + 1) => a + b;

console.log(greet());
console.log(greet(undefined));
console.log(greet(null));
console.log(add());
console.log(add(5));
