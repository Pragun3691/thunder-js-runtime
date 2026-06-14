let values = [10, 20, 30];

for (const value of values) {
    if (value === 20) {
        continue;
    }
    console.log(value);
}

for (const letter of "JS") {
    console.log(letter);
}

values.forEach((value, index, original) => {
    console.log(index + ": " + value + " / " + original.length);
});

console.log(Array.isArray(values));
console.log(Array.isArray({}));

let user = { name: "Pragun", age: 20 };

console.log(Object.keys(user).join(", "));
console.log(Object.values(user).join(", "));
console.log(
    Object.entries(user)
        .map(entry => entry.join(": "))
        .join(", ")
);
