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
const input = getArg('--input', 'runtime/input.mp4');
const recipePath = path.resolve(process.cwd(), getArg('--recipe', 'public/runtime/edit_recipe.json'));
const output = path.resolve(process.cwd(), getArg('--output', '../output/final_video.mp4'));
const recipe = JSON.parse(fs.readFileSync(recipePath, 'utf-8'));
const entry = path.join(__dirname, 'src', 'Root.tsx');
const serveUrl = await bundle(entry);
const logoConfig = recipe.logo ?? {};
const inputVideoSrc = recipe.input_video?.src ?? 'runtime/input.mp4';
const logoSrc = logoConfig.enabled !== false && logoConfig.path ? logoConfig.path : undefined;
const logoFallback = logoConfig.fallback_text ?? 'Hamsa Nomads';
const inputProps = {inputVideoSrc, recipe, logoSrc, logoFallback, runtimeRecipePath: 'runtime/edit_recipe.json'};
console.log(`Remotion static input: ${inputVideoSrc}`);
console.log(`Remotion static logo: ${logoSrc ?? 'fallback text only'}`);
console.log(`Remotion recipe: ${recipePath}`);
console.log(`Remotion output: ${output}`);
console.log(`Remotion staged input argument: ${input}`);
const composition = await selectComposition({serveUrl, id: 'HamsaVideo', inputProps});
await renderMedia({composition, serveUrl, codec: 'h264', outputLocation: output, inputProps, chromiumOptions: {disableWebSecurity: true}});
try {
  await renderStill({composition, serveUrl, output: path.join(path.dirname(output), 'thumbnail.jpg'), inputProps, frame: 45});
} catch (error) {
  console.warn('Thumbnail still failed:', error.message);
}
console.log(`Rendered ${output}`);
