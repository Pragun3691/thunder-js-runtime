console.log(0 ** -1);
console.log(Math.pow(0, -1));

let a = [9];
let i = 0;
a[i++] = i;
console.log(a[0]);
console.log(i);

let b = [1, 2];
let j = 0;
console.log(b[j++]++);
console.log(j);
console.log(b);

let value = null;
console.log(value?.profile.name);

let user = {};
console.log(user?.missing?.());

let values = [1, 2];
console.log(values["length"]);
console.log(values["join"](","));

console.log("abc"["length"]);
console.log("abc"["toUpperCase"]());

let indexes = [10, 20];
console.log(indexes[1.9]);
console.log(indexes["01"]);
console.log(indexes["1"]);

switch (1) {
    case 1:
        let hidden = 7;
        break;
}

console.log(typeof hidden);

const factorial = function inner(n) {
    return n <= 1 ? 1 : n * inner(n - 1);
};

console.log(factorial(5));
console.log(typeof inner);
