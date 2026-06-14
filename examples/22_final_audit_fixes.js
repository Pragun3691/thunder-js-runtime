let user = {
    name: "Pragun",
    age: 20
};

console.log([1, 2, 3]);
console.log([[1, 2], [3, 4]]);
console.log(user);
console.log("hello", [1, 2]);

console.log(String([1, 2, 3]));
console.log(`${[1, 2, 3]}`);
console.log([null, undefined].join(", "));

for (const key in user) {
    console.log(key);
}

for (const index in ["a", "b"]) {
    console.log(index);
}

console.log([1, 2] + [3, 4]);
console.log([1, 2] + "");
console.log("" + { a: 1 });
console.log({ a: 1 } + 5);
console.log([] + []);
console.log([] + 1);
console.log(2 + 3);
