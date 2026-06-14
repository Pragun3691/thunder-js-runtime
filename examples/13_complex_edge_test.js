function makeMultiplier(multiplier) {
    return value => value * multiplier;
}

function analyse(values, transform) {
    let cleaned = values
        .filter(value => value !== null && value !== undefined)
        .map((value, index) => transform(Number(value)) + index);

    let total = cleaned.reduce((sum, value) => sum + value, 0);

    return {
        cleaned: cleaned,
        total: total,
        hasLargeValue: cleaned.some(value => value > 20),
        allNonNegative: cleaned.every(value => value >= 0),
        firstEven: cleaned.find(value => value % 2 === 0)
    };
}

let original = [0, "2", null, 4, undefined, -1];
let cloned = [...original];

cloned.push(10);
cloned.shift();

const multiplyByThree = makeMultiplier(3);
const result = analyse(cloned, multiplyByThree);

console.log("Original: " + original.join(", "));
console.log("Cloned: " + cloned.join(", "));
console.log("Cleaned: " + result.cleaned.join(", "));
console.log("Total: " + result.total);
console.log("Large: " + result.hasLargeValue);
console.log("Non-negative: " + result.allNonNegative);
console.log("First even: " + result.firstEven);

switch (result.total) {
    case 44:
        console.log("Exact total");
        break;
    default:
        console.log("Unexpected total");
}

let count = 0;

do {
    count++;
    if (count === 2) {
        continue;
    }

    console.log("Count: " + count);
} while (count < 3);

const epoch = new Date(0);
console.log(epoch.toISOString());