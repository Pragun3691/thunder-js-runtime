let [a, , c = 30, ...rest] = [1, 2, undefined, 4, 5];

console.log(a);
console.log(c);
console.log(rest);

let user = {
    name: "Pragun",
    score: undefined,
    active: false,
    extra: 99
};

let {
    name: userName,
    score = 10,
    active = true,
    ...remaining
} = user;

console.log(userName);
console.log(score);
console.log(active);
console.log(remaining);

function describe({ name = "World", age = 0 } = {}) {
    return `${name}:${age}`;
}

const pairSum = ([x, y = 5]) => x + y;

console.log(describe());
console.log(describe({ name: "A", age: 20 }));
console.log(pairSum([3]));
console.log([{ x: 1 }, { x: 2 }].map(({ x }) => x * 10));
