# Implementation Plan: Advanced Documentation System

## Overview

Implement the documentation platform incrementally: core types and data models first, then individual UI components, then the build pipeline and search integration, and finally version control and wiring. Each task builds directly on the previous ones with no orphaned code.

## Tasks

- [ ] 1. Set up project structure, types, and data models
  - Create `docs/` directory structure with `api/`, `guides/`, `tutorials/` subdirectories and version subdirectories (`docs/v1/`, `docs/v2/`)
  - Define all TypeScript interfaces in `src/types/docs.ts`: `Frontmatter`, `Tutorial`, `TutorialStep`, `TutorialProgress`, `SearchIndexEntry`, `VersionManifest`, `VersionMeta`, `CodeExample`, `APIEndpoint`, `GuideStep`, `SearchResult`, `PageProps`
  - Define `SupportedLanguage` union type and `HttpMethod` type
  - _Requirements: 1.1, 2.1, 3.1, 4.3, 7.1_

- [ ] 2. Implement tutorial progress persistence utilities
  - [ ] 2.1 Create `src/lib/tutorialProgress.ts` with `saveTutorialProgress` and `loadTutorialProgress` functions using localStorage keyed by tutorial ID
    - Handle missing/malformed localStorage entries gracefully
    - _Requirements: 3.2, 3.3, 3.4_

  - [ ]* 2.2 Write property test for tutorial progress round-trip
    - **Property 1: Tutorial progress round-trip**
    - **Validates: Requirements 3.4**
    - Generate random tutorial IDs and step indices with fast-check, save then restore, assert step index is identical

- [ ] 3. Implement CodeBlock component
  - [ ] 3.1 Create `src/components/CodeBlock.tsx` with syntax highlighting via a library such as `react-syntax-highlighter` or `shiki`, copy button, and optional Sandpack sandbox for runnable examples
    - Support all five `SupportedLanguage` values
    - Copy button writes to clipboard and shows a confirmation indicator for 2 seconds
    - Display inline error output when execution fails
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 3.2 Write property test for copy action
    - **Property 2: Copy action delivers full code content**
    - **Validates: Requirements 4.2**
    - Generate random code strings (unicode, whitespace, special chars) with fast-check, trigger `handleCopy`, assert clipboard equals original string

  - [ ]* 3.3 Write property test for code example language support
    - **Property 9: Code example language support**
    - **Validates: Requirements 4.1, 4.3**
    - Generate random code strings for each supported language, pass to `renderCodeBlock`, assert no exception and output contains a highlighted element

  - [ ]* 3.4 Write unit tests for CodeBlock
    - Test copy confirmation disappears after 2 seconds
    - Test runnable sandbox renders and displays execution output
    - Test error output is shown inline when execution fails
    - _Requirements: 4.2, 4.4, 4.5_

- [ ] 4. Implement VideoPlayer component
  - [ ] 4.1 Create `src/components/VideoPlayer.tsx` with responsive embed supporting `youtube`, `vimeo`, and `self-hosted` providers
    - Render transcript/summary below the player
    - Show fallback placeholder with transcript link when source is unavailable
    - Do not auto-navigate while video is playing
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 4.2 Write unit tests for VideoPlayer
    - Test transcript renders below player
    - Test fallback placeholder and transcript link render when src is unavailable
    - _Requirements: 5.2, 5.4_

- [ ] 5. Implement version utilities and VersionSelector component
  - [ ] 5.1 Create `src/lib/versionUtils.ts` with `sortVersions(versions: VersionMeta[]): VersionMeta[]` (descending semver) and `buildVersionedUrl(version: string, slug: string): string`
    - _Requirements: 7.2, 7.5_

  - [ ]* 5.2 Write property test for version selector ordering invariant
    - **Property 5: Version selector ordering invariant**
    - **Validates: Requirements 7.5**
    - Generate random `VersionMeta` arrays with fast-check, pass to `sortVersions`, assert strictly descending order and `isLatest` item is first

  - [ ]* 5.3 Write property test for versioned page routing consistency
    - **Property 6: Versioned page routing consistency**
    - **Validates: Requirements 7.2**
    - Generate random version strings and slugs with fast-check, call `buildVersionedUrl`, assert URL contains both version and slug as path segments

  - [ ] 5.4 Create `src/components/VersionSelector.tsx` dropdown that routes to the equivalent page in the selected version
    - Default to latest version; list all versions in descending order
    - _Requirements: 7.2, 7.5_

  - [ ]* 5.5 Write unit tests for VersionSelector
    - Test versions render in descending order with latest selected by default
    - _Requirements: 7.5_

- [ ] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement InteractiveGuide component
  - [ ] 7.1 Create `src/components/InteractiveGuide.tsx` managing step state, rendering current step MDX content, and calling `onComplete` when all steps are finished
    - Display completion indicator and link to next recommended resource on finish
    - Display error message and static fallback link when content fails to load
    - Wrap in an error boundary so failures don't crash the page
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 7.2 Write property test for interactive guide step state update
    - **Property 10: Interactive guide step state update**
    - **Validates: Requirements 1.2**
    - Generate random guide step sequences with fast-check, simulate a step interaction, assert rendered step ID matches next step and not previous

  - [ ]* 7.3 Write unit tests for InteractiveGuide
    - Test completion indicator and next-resource link appear after last step
    - Test error message and fallback link render when content load fails
    - _Requirements: 1.3, 1.4_

- [ ] 8. Implement TutorialPlayer component and tutorial index page
  - [ ] 8.1 Create `src/components/TutorialPlayer.tsx` that reads initial step from localStorage via `loadTutorialProgress`, renders steps in order, updates progress on step completion, and saves to localStorage
    - _Requirements: 3.2, 3.3, 3.4_

  - [ ] 8.2 Create `src/pages/tutorials/index.tsx` listing all tutorials grouped by topic and difficulty
    - _Requirements: 3.1, 3.5_

  - [ ]* 8.3 Write unit tests for TutorialPlayer
    - Test correct step is restored from localStorage on mount
    - Test progress indicator updates when a step is completed
    - Test navigation to next step is enabled after step completion
    - _Requirements: 3.2, 3.3, 3.4_

- [ ] 9. Implement APIReferenceRenderer and 404/error pages
  - [ ] 9.1 Create `src/components/APIReferenceRenderer.tsx` rendering method, path, parameters, request body, responses, and code examples for a single endpoint
    - _Requirements: 2.1, 2.3_

  - [ ] 9.2 Create `src/pages/404.tsx` with a link to the API reference index; create `src/pages/api-reference/404.tsx` for missing API reference pages
    - Handle deprecated version URL redirects with a deprecation notice
    - Handle page-not-found-in-version with a link to the version index
    - _Requirements: 2.5, 7.4, 7.6_

  - [ ] 9.3 Add a version banner component rendered on non-latest version pages linking to the equivalent latest-version page
    - _Requirements: 7.3_

  - [ ]* 9.4 Write unit tests for APIReferenceRenderer and error pages
    - Test all required fields render (method, path, parameters, responses, examples)
    - Test 404 page renders correct message and index link
    - Test deprecation redirect page renders deprecation notice
    - Test version banner renders on non-latest pages
    - _Requirements: 2.1, 2.5, 7.3, 7.4, 7.6_

- [ ] 10. Implement SearchBar component and search service integration
  - [ ] 10.1 Create `src/lib/searchClient.ts` wrapping the Meilisearch (or Algolia DocSearch) client, exposing a `search(query: string): Promise<SearchResult[]>` function
    - Return empty array and surface unavailable state when service is unreachable
    - _Requirements: 6.2, 6.6_

  - [ ] 10.2 Create `src/components/SearchBar.tsx` that calls `searchClient.search` for queries ≥ 2 characters and renders ranked results with title, excerpt, and URL
    - Show no-results message with related links when query returns nothing
    - Show "search unavailable" message with site map link when service is down
    - _Requirements: 6.2, 6.3, 6.4, 6.6_

  - [ ]* 10.3 Write property test for search results display fields
    - **Property 3: Search results contain required display fields**
    - **Validates: Requirements 6.3**
    - Generate random `SearchResult` arrays with fast-check, assert every result has non-empty `pageTitle`, non-empty `excerpt`, and a `url` starting with `/`

  - [ ]* 10.4 Write unit tests for SearchBar
    - Test results render title, excerpt, and URL
    - Test no-results message and related links appear for empty result set
    - Test search unavailable message and site map link appear when service is down
    - _Requirements: 6.3, 6.4, 6.6_

- [ ] 11. Implement build-time search indexer and API reference generator
  - [ ] 11.1 Create `scripts/buildSearchIndex.ts` that walks all `docs/` MDX files, strips MDX to plain text, and produces `SearchIndexEntry` objects pushed to the search service
    - Index all page types: guides, tutorials, API reference, and code examples
    - _Requirements: 6.1, 6.5_

  - [ ] 11.2 Create `scripts/generateAPIReference.ts` that reads the OpenAPI schema and emits MDX files under `docs/api/` with all required endpoint fields and at least one code example per endpoint
    - _Requirements: 2.1, 2.3, 2.4_

  - [ ]* 11.3 Write unit tests for build scripts
    - Test `buildSearchIndex` emits a `SearchIndexEntry` for every MDX file found
    - Test `generateAPIReference` emits one MDX file per endpoint with required fields
    - _Requirements: 2.1, 6.1_

- [ ] 12. Implement DocumentationPage and wire all components together
  - [ ] 12.1 Create `src/components/DocumentationPage.tsx` that accepts `PageProps` and delegates to `InteractiveGuide`, `TutorialPlayer`, `APIReferenceRenderer`, `CodeBlock`, `VideoPlayer`, `SearchBar`, and `VersionSelector` based on `pageType` and frontmatter
    - Apply error boundaries around `InteractiveGuide` and `CodeBlock`
    - _Requirements: 1.1, 2.2, 3.1, 4.1, 5.1, 7.1_

  - [ ] 12.2 Create Next.js dynamic route `src/pages/[version]/[...slug].tsx` using `getStaticProps` and `getStaticPaths` to statically generate all versioned documentation pages
    - Render version banner for non-latest versions
    - Handle redirect for deprecated version URLs
    - _Requirements: 7.1, 7.2, 7.3, 7.6_

  - [ ]* 12.3 Write integration tests for DocumentationPage routing
    - Test tutorial page restores progress and renders player
    - Test API reference page renders within 2 seconds
    - Test version selector navigates to correct versioned URL
    - _Requirements: 2.2, 3.4, 7.2_

- [ ] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use **fast-check** with a minimum of 100 iterations each
- Properties 4, 7, and 8 (index propagation timing, render latency, search response time) are validated through integration/performance tests outside this task list
- Error boundaries wrap `InteractiveGuide` and `CodeBlock` so component failures don't crash the page
