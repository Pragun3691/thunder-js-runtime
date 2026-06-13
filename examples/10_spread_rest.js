function sum(...numbers) {
    return numbers.reduce((total, value) => total + value, 0);
}

const collect = (first, ...rest) => first + ": " + rest.join(", ");

let values = [1, 2, 3];

console.log(sum(...values));
console.log(collect("A", "B", "C"));
