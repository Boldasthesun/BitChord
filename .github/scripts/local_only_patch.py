#!/usr/bin/env python3
"""Local-only patch for BitChord.

Turns the app into a local-music player: no YouTube Music, four tabs, and the
device's own music throughout.

  * Home    every track on the device, under the app's mark
  * Albums  the Local Music page on its Albums segment
  * Library the same page, holding playlists and folders
  * Search  the app's search, reading the device

Every edit asserts that it matched, so a source change upstream fails the build
loudly instead of producing a half-patched app.
"""
import sys, pathlib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
EDITS = []


def edit(path, old, new, count=1):
    EDITS.append((path, old, new, count))


MAIN = "app/src/main/java/com/music/bitchord/MainActivity.kt"
VM = "app/src/main/java/com/music/bitchord/ui/MainViewModel.kt"
SETTINGS = "app/src/main/java/com/music/bitchord/data/settings/AppSettings.kt"
REG = "app/src/main/java/com/music/bitchord/data/sources/SourceRegistry.kt"
SRC_SCREEN = "app/src/main/java/com/music/bitchord/ui/screens/SourcesScreen.kt"
GRADLE = "app/build.gradle.kts"
NEW_SCREEN_PATH = "app/src/main/java/com/music/bitchord/ui/screens/LocalSongsScreen.kt"
NEW_SCREEN = r"""package com.music.bitchord.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.music.bitchord.data.model.Song
import com.music.bitchord.data.model.UiState
import com.music.bitchord.sharedui.resources.Res as SharedRes
import com.music.bitchord.sharedui.resources.ic_logo
import com.music.bitchord.ui.components.SongRow
import org.jetbrains.compose.resources.painterResource

/**
 * Local-only build: the home tab is every track on the device, under the app's
 * mark where the original home carried it — no page header, no artwork, no
 * Play/Shuffle block, because those belong to the release page Albums and
 * Library show.
 */
@Composable
fun LocalSongsScreen(
    songsState: UiState<List<Song>>,
    contentPadding: PaddingValues,
    onPlay: (List<Song>, Int) -> Unit,
    onRequestPermission: () -> Unit,
) {
    val songs = (songsState as? UiState.Success<List<Song>>)?.data.orEmpty()
    Column(modifier = Modifier.fillMaxSize()) {
        Icon(
            painter = painterResource(SharedRes.drawable.ic_logo),
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onBackground,
            modifier = Modifier
                .padding(start = 20.dp, top = 14.dp, bottom = 10.dp)
                .height(26.dp)
                .aspectRatio(730f / 484f),
        )
        when {
            songsState is UiState.Error -> LocalSongsMessage(
                message = songsState.message,
                action = "Allow access",
                onAction = onRequestPermission,
            )
            songsState is UiState.Loading -> LocalSongsMessage(
                message = "Reading your music...",
                action = null,
                onAction = null,
            )
            songs.isEmpty() -> LocalSongsMessage(
                message = "No music yet. Point Local music folder at your files in Settings.",
                action = null,
                onAction = null,
            )
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = contentPadding,
            ) {
                itemsIndexed(songs, key = { _, song -> song.videoId }) { index, song ->
                    SongRow(song = song, onClick = { onPlay(songs, index) })
                }
            }
        }
    }
}

@Composable
private fun LocalSongsMessage(
    message: String,
    action: String?,
    onAction: (() -> Unit)?,
) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(32.dp),
        ) {
            Text(text = message, style = MaterialTheme.typography.bodyMedium)
            if (action != null && onAction != null) {
                Spacer(Modifier.height(16.dp))
                Button(onClick = onAction) { Text(action) }
            }
        }
    }
}
"""

# --- The app name -------------------------------------------------------------
edit(GRADLE,
     'resValue("string", "app_name", "BitChord Dev")',
     'resValue("string", "app_name", "Music")')

# --- MainActivity: the home tab reads the device, nothing reads a feed --------
edit(MAIN,
     """    var selectedTab by rememberSaveable { mutableIntStateOf(0) }
    // Explore loads the first time it's shown, not at launch beside Home.
    LaunchedEffect(selectedTab) {
        if (selectedTab == TAB_EXPLORE) viewModel.onExploreShown()
    }""",
     """    var selectedTab by rememberSaveable { mutableIntStateOf(0) }
    // Local-only build: the home tab lists the device's own music.
    val localSongs by viewModel.allLibrarySongs.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        viewModel.loadLibrarySongs()
    }""")

# --- MainActivity: import the home screen -------------------------------------
edit(MAIN,
     "import com.music.bitchord.ui.screens.LocalFolderTab",
     "import com.music.bitchord.ui.screens.LocalFolderTab\n"
     "import com.music.bitchord.ui.screens.LocalSongsScreen")

edit(MAIN,
     """    val currentFeed = when {
        route != null || detail != null -> null
        selectedTab == TAB_HOME -> MainViewModel.Feed.HOME
        selectedTab == TAB_EXPLORE -> MainViewModel.Feed.EXPLORE
        selectedTab == TAB_LIBRARY -> MainViewModel.Feed.LIBRARY
        else -> null
    }""",
     """    // Local-only build: no tab reads a catalogue feed.
    val currentFeed: MainViewModel.Feed? = null""")

# --- MainActivity: Home, Albums, Library, Search ------------------------------
edit(MAIN,
     """    val tabs = remember(homeLabel, exploreLabel, libraryLabel, searchLabel) {
        listOf(
            BottomTab(homeLabel, BitChordIcons.Home),
            BottomTab(exploreLabel, BitChordIcons.TabExplore),
            BottomTab(libraryLabel, BitChordIcons.TabLibrary),
            BottomTab(searchLabel, BitChordIcons.TabSearch),
        )
    }""",
     """    val albumsLabel = stringResource(R.string.albums)
    // Local-only build: every song, the albums, the playlists and folders, and
    // a search over the device.
    val tabs = remember(homeLabel, albumsLabel, libraryLabel, searchLabel) {
        listOf(
            BottomTab(homeLabel, BitChordIcons.Home),
            BottomTab(albumsLabel, BitChordIcons.GridView),
            BottomTab(libraryLabel, BitChordIcons.TabLibrary),
            BottomTab(searchLabel, BitChordIcons.TabSearch),
        )
    }""")

# --- MainActivity: what each tab shows ---------------------------------------
edit(MAIN,
     """                val onTabSelected: (Int) -> Unit = { index ->
                    navigator.clear()
                    viewModel.closeMoodGenre()
                    selectedTab = index

                    // Every search tab tap resets the field, focuses it, and opens
                    // the keyboard through SearchScreen's focus request.
                    if (index == TAB_SEARCH) {
                        viewModel.onQueryChange("")
                        searchFocusRequested = true
                    }
                }""",
     """                val onTabSelected: (Int) -> Unit = { index ->
                    navigator.clear()
                    viewModel.closeMoodGenre()
                    selectedTab = index
                    when (index) {
                        TAB_SEARCH -> {
                            // Local-only build: search reads the device's own
                            // library, so the page under it has to go.
                            viewModel.clearDetail()
                            viewModel.onQueryChange("")
                            viewModel.loadLibrarySongs()
                            searchFocusRequested = true
                        }
                        TAB_HOME -> {
                            // Home is the flat list, not the release page.
                            viewModel.clearDetail()
                        }
                        else -> {
                            // Albums and Library are two views of the one Local
                            // Music page.
                            localFolderStates.getOrPut("local:all") { LocalFolderState() }.tab =
                                if (index == TAB_LIBRARY) {
                                    LocalFolderTab.PLAYLISTS
                                } else {
                                    LocalFolderTab.ALBUMS
                                }
                            if (viewModel.detailStack.value.lastOrNull()?.browseId != "local:all") {
                                viewModel.clearDetail()
                                viewModel.openDetail(
                                    browseId = "local:all",
                                    title = context.getString(R.string.local_music),
                                    subtitle = context.getString(R.string.audio_files_on_device),
                                )
                            }
                        }
                    }
                }""")

# --- MainActivity: the home list, and the page behind the other two tabs -----
edit(MAIN,
     "                        } else when ((destination as? AppDestination.Tab)?.index ?: selectedTab) {",
     """                        } else if (route == null && detail == null && selectedTab == TAB_HOME) {
                            // Local-only build: every track on the device, under
                            // the app's mark rather than a page header.
                            LocalSongsScreen(
                                songsState = localSongs,
                                contentPadding = listPadding,
                                onPlay = { songs, index ->
                                    playFrom(
                                        songs,
                                        index,
                                        QueueSource(
                                            context.getString(R.string.local_music),
                                            PlaybackSourceType.QUEUE,
                                        ),
                                    )
                                },
                                onRequestPermission = {
                                    mediaPermissionLauncher.launch(mediaPermission)
                                },
                            )
                        } else if (route == null && detail == null && selectedTab <= TAB_LIBRARY) {
                            // Local-only build: Albums and Library are the Local
                            // Music page, which this opens if it is not already up.
                            LaunchedEffect(selectedTab) {
                                if (!LocalMediaRepository.hasStoragePermission(context)) {
                                    mediaPermissionLauncher.launch(mediaPermission)
                                }
                                if (viewModel.detailStack.value.none { it.browseId == "local:all" }) {
                                    viewModel.openDetail(
                                        browseId = "local:all",
                                        title = context.getString(R.string.local_music),
                                        subtitle = context.getString(R.string.audio_files_on_device),
                                    )
                                }
                            }
                            Box(Modifier.fillMaxSize())
                        } else when ((destination as? AppDestination.Tab)?.index ?: selectedTab) {""")

# --- MainActivity: the page's own segment control drives the bar too ---------
edit(MAIN,
     "    val localFolderStates = remember { mutableMapOf<String, LocalFolderState>() }",
     """    val localFolderStates = remember { mutableMapOf<String, LocalFolderState>() }
    // Local-only build: the bottom bar and the page's own segmented control are
    // two views of one choice, so each follows the other.
    val localMusicPageState = localFolderStates.getOrPut("local:all") { LocalFolderState() }
    LaunchedEffect(localMusicPageState.tab) {
        val index = when (localMusicPageState.tab) {
            LocalFolderTab.ALBUMS -> TAB_EXPLORE
            LocalFolderTab.PLAYLISTS, LocalFolderTab.FOLDERS -> TAB_LIBRARY
            // Songs and Artists have no tab of their own: the page is already
            // open on Albums, and moving the bar under it would lie.
            else -> selectedTab
        }
        if (selectedTab != index) selectedTab = index
    }""")

# --- MainActivity: the Library tab holds playlists and folders only ----------
edit(MAIN,
     "                                    tabs = if (isDevice) LocalFolderTab.DEVICE else LocalFolderTab.BASIC,",
     """                                    tabs = when {
                                        !isDevice -> LocalFolderTab.BASIC
                                        // Local-only build: the Library tab is the
                                        // playlists and the folders, nothing else.
                                        selectedTab == TAB_LIBRARY -> listOf(
                                            LocalFolderTab.PLAYLISTS,
                                            LocalFolderTab.FOLDERS,
                                        )
                                        else -> LocalFolderTab.DEVICE
                                    },""")

# --- MainViewModel: the device listing, and no launch feed -------------------
edit(VM,
     "    private val _librarySongs = MutableStateFlow<UiState<List<Song>>>(UiState.Loading)",
     "    private val _librarySongs = MutableStateFlow<UiState<List<Song>>>(UiState.Loading)\n\n"
     "    /** The same listing, for the local-only home tab. */\n"
     "    val allLibrarySongs: StateFlow<UiState<List<Song>>> = _librarySongs.asStateFlow()")

edit(VM,
     """        startTypeaheadMediaPipeline()
        loadHome()""",
     """        startTypeaheadMediaPipeline()
        // Local-only build: the home feed is not loaded at launch.""")

# --- MainViewModel: search reads the device, not a catalogue -----------------
edit(VM,
     "    private val _searchSource = MutableStateFlow(SearchSource.YOUTUBE)",
     "    // Local-only build: the search tab reads the device's own library.\n"
     "    private val _searchSource = MutableStateFlow(SearchSource.LIBRARY)")

# --- No "Playing from" caption on the player ---------------------------------
edit(SETTINGS,
     "    val hideSongStatus = MutableStateFlow(false)",
     "    // Local-only build: there is no catalogue to name, so the caption is off.\n"
     "    val hideSongStatus = MutableStateFlow(true)")
edit(SETTINGS,
     "        hideSongStatus.value = prefs.getBoolean(KEY_HIDE_SONG_STATUS, false)",
     "        hideSongStatus.value = prefs.getBoolean(KEY_HIDE_SONG_STATUS, true)")

# --- No YouTube account card in Settings -------------------------------------
edit("app/src/main/java/com/music/bitchord/ui/screens/AccountAndScrobblingScreen.kt",
     """        SettingsGroup(
            footer = if (signedIn) stringResource(R.string.account_profiles_help) else null,
            topSpacing = 0.dp,
        ) {
            AccountCard(
                signedIn = signedIn,
                account = account,
                onSignIn = onSignIn,
                onClick = onSwitchChannel,
                grouped = true,
            )
            if (signedIn) {
                FullWidthDivider()
                SettingsRow(
                    icon = SfIcons.SwitchAccount,
                    title = stringResource(R.string.listen_as),
                    subtitle = channelName ?: stringResource(R.string.default_youtube_profile),
                    onClick = onSwitchChannel,
                )
                FullWidthDivider()
                DestructiveRow(label = stringResource(R.string.sign_out), onClick = onSignOut)
            }
        }
""",
     """        // Local-only build: there is no account to sign in to, so the card that
        // offered it is gone. Scrobbling and the rest of the page stay.
""")

# --- YouTube off by default, and unable to be switched back on --------------
edit(REG,
     ".map { SourceConfig(kind = it) }",
     ".map { SourceConfig(kind = it, enabled = it != SourceKind.YOUTUBE) }")
edit(REG,
     "                    config.kind == SourceKind.YOUTUBE && !config.enabled -> config.copy(enabled = true)\n",
     "")
edit(REG,
     "        if (!enabled && config(configId)?.kind == SourceKind.YOUTUBE) return\n",
     "")

# --- Do not list YouTube on the sources screen ------------------------------
edit(SRC_SCREEN,
     "val fixed = configs.filterNot { it.kind.isUserAdded }",
     "val fixed = configs.filterNot { it.kind.isUserAdded || it.kind == SourceKind.YOUTUBE }")


def main():
    target = ROOT / NEW_SCREEN_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(NEW_SCREEN, encoding="utf-8")
    print("ok    added", NEW_SCREEN_PATH)

    total = 0
    for rel, old, new, count in EDITS:
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        found = text.count(old)
        if found != count:
            print(f"FAIL  {rel}: expected {count} match(es), found {found}")
            print("----- looking for -----")
            print(old[:400])
            return 1
        p.write_text(text.replace(old, new), encoding="utf-8")
        total += found
        print(f"ok    {rel}: {found} edit(s)")

    print("\nApplied", total, "edits and added 1 file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
