import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition, renderStill} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const getArg = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
};
const input = path.resolve(process.cwd(), getArg('--input', '../input/test.mp4'));
const recipePath = path.resolve(process.cwd(), getArg('--recipe', '../output/edit_recipe.json'));
const output = path.resolve(process.cwd(), getArg('--output', '../output/final_video.mp4'));
const recipe = JSON.parse(fs.readFileSync(recipePath, 'utf-8'));
const entry = path.join(__dirname, 'src', 'Root.tsx');
const serveUrl = await bundle(entry);
const inputProps = {inputVideo: input, recipe};
const composition = await selectComposition({serveUrl, id: 'HamsaVideo', inputProps});
await renderMedia({composition, serveUrl, codec: 'h264', outputLocation: output, inputProps, chromiumOptions: {disableWebSecurity: true}});
try {
  await renderStill({composition, serveUrl, output: path.join(path.dirname(output), 'thumbnail.jpg'), inputProps, frame: 45});
} catch (error) {
  console.warn('Thumbnail still failed:', error.message);
}
console.log(`Rendered ${output}`);
