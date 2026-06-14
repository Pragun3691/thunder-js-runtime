var users = [
    { name: "A", score: 10 },
    { name: "B", score: 20 },
];

var labels = users.map(({ name, score = 0 }) => `${name}:${score}`);
var [first, ...others] = labels;

console.log(first);
console.log(others);
