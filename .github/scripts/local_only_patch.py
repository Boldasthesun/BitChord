#!/usr/bin/env python3
"""Local-only patch for BitChord: no YouTube Music, three local tabs.

Applies a small, surgical set of edits to the checked-out source and adds one
new screen file:

  * the bottom bar becomes Songs / Playlists / Folders, all drawn from the
    device's own music, and the app opens on Songs
  * YouTube Music is seeded disabled, hidden from the sources screen, and can
    no longer be switched back on
  * the home feed is no longer loaded at launch, so nothing calls a catalogue

Every edit asserts that it matched, so a source change upstream fails the build
loudly instead of producing a half-patched app.
"""
import sys, pathlib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
EDITS = []

NEW_SCREEN_PATH = "app/src/main/java/com/music/bitchord/ui/screens/LocalHomeScreen.kt"
NEW_SCREEN = r"""package com.music.bitchord.ui.screens

import android.content.Context
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.music.bitchord.data.LocalGroups
import com.music.bitchord.data.OfflinePlaylists
import com.music.bitchord.data.model.Song
import com.music.bitchord.data.model.UiState
import com.music.bitchord.ui.components.SongRow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Local-only build: the four bottom tabs draw the device's own music.
 *
 * Songs lists every track the Local Music folder holds and plays from the row
 * that was tapped. Albums and Folders group the same tracks by their tags and
 * by the directory they sit in. Playlists lists the offline player's own
 * playlists, Liked first.
 *
 * A folder can be hidden from the Folders tab. Hiding it takes its tracks out
 * of every tab — the lists, the album groupings and the playlists alike — and
 * the hidden ones stay listed at the bottom of Folders so nothing is lost and
 * nothing needs a settings screen to bring back.
 *
 * [tab] is the bottom tab's index, which is the same value the rest of the app
 * calls [com.music.bitchord.MainActivity]'s TAB_* constants.
 */
@Composable
fun LocalHomeScreen(
    tab: Int,
    songsState: UiState<List<Song>>,
    contentPadding: PaddingValues,
    onPlay: (List<Song>, Int) -> Unit,
    onRequestPermission: () -> Unit,
) {
    val context = LocalContext.current
    LaunchedEffect(Unit) { HiddenFolders.load(context) }
    val hidden by HiddenFolders.hidden.collectAsStateWithLifecycle()

    val songs = (songsState as? UiState.Success<List<Song>>)?.data.orEmpty()
    val visible = remember(songs, hidden) { songs.filterNot { it.isInHiddenFolder(hidden) } }
    val onToggle: (String) -> Unit = { path -> HiddenFolders.toggle(context, path) }

    when {
        songsState is UiState.Loading -> LocalMessage(
            message = "Reading your music...",
            action = null,
            onAction = null,
            contentPadding = contentPadding,
        )
        songsState is UiState.Error -> LocalMessage(
            message = songsState.message,
            action = "Allow access",
            onAction = onRequestPermission,
            contentPadding = contentPadding,
        )
        songs.isEmpty() -> LocalMessage(
            message = "No music yet. Point Local music folder at your files in Settings.",
            action = null,
            onAction = null,
            contentPadding = contentPadding,
        )
        // Folders stays reachable however little is left, so the last hidden
        // folder can always be brought back from inside the app.
        tab == 3 -> LocalFolders(visible, hidden, onToggle, contentPadding, onPlay)
        visible.isEmpty() -> LocalMessage(
            message = "Everything here is hidden. Open Folders to bring it back.",
            action = null,
            onAction = null,
            contentPadding = contentPadding,
        )
        tab == 1 -> LocalAlbums(visible, contentPadding, onPlay)
        tab == 2 -> LocalPlaylists(hidden, contentPadding, onPlay)
        else -> LocalSongs(visible, contentPadding, onPlay)
    }
}

@Composable
private fun LocalSongs(
    songs: List<Song>,
    contentPadding: PaddingValues,
    onPlay: (List<Song>, Int) -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = contentPadding,
    ) {
        itemsIndexed(songs, key = { _, song -> song.videoId }) { index, song ->
            SongRow(song = song, onClick = { onPlay(songs, index) })
        }
    }
}

@Composable
private fun LocalAlbums(
    songs: List<Song>,
    contentPadding: PaddingValues,
    onPlay: (List<Song>, Int) -> Unit,
) {
    val albums = remember(songs) { LocalGroups.albumsOf("local:all", songs, emptyList()) }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = contentPadding,
    ) {
        items(albums, key = { it.browseId }) { album ->
            LocalGroupRow(
                title = album.title,
                subtitle = album.subtitle.ifBlank { "${album.songs.size} songs" },
                onClick = { if (album.songs.isNotEmpty()) onPlay(album.songs, 0) },
            )
        }
    }
}

@Composable
private fun LocalPlaylists(
    hidden: Set<String>,
    contentPadding: PaddingValues,
    onPlay: (List<Song>, Int) -> Unit,
) {
    val playlists by OfflinePlaylists.playlists.collectAsStateWithLifecycle()
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = contentPadding,
    ) {
        items(playlists, key = { it.id }) { playlist ->
            val shown = playlist.songs.filterNot { it.isInHiddenFolder(hidden) }
            LocalGroupRow(
                title = playlist.title,
                subtitle = "${shown.size} songs",
                onClick = { if (shown.isNotEmpty()) onPlay(shown, 0) },
            )
        }
    }
}

@Composable
private fun LocalFolders(
    songs: List<Song>,
    hidden: Set<String>,
    onToggle: (String) -> Unit,
    contentPadding: PaddingValues,
    onPlay: (List<Song>, Int) -> Unit,
) {
    val folders = remember(songs) { LocalGroups.foldersOf("local:all", songs) }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = contentPadding,
    ) {
        items(folders, key = { it.browseId }) { folder ->
            LocalGroupRow(
                title = folder.title,
                subtitle = folder.subtitle.ifBlank { "${folder.songs.size} songs" },
                onClick = { if (folder.songs.isNotEmpty()) onPlay(folder.songs, 0) },
                actionLabel = "Hide",
                onAction = { folder.songs.firstOrNull()?.folderPath()?.let(onToggle) },
            )
        }
        if (hidden.isNotEmpty()) {
            item(key = "hidden-heading") {
                Text(
                    text = "Hidden folders",
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 20.dp, bottom = 4.dp),
                )
            }
            items(hidden.sorted(), key = { "hidden:$it" }) { path ->
                LocalGroupRow(
                    title = path.substringAfterLast('/').ifBlank { path },
                    subtitle = "Hidden from all tabs",
                    onClick = {},
                    actionLabel = "Unhide",
                    onAction = { onToggle(path) },
                )
            }
        }
    }
}

@Composable
private fun LocalGroupRow(
    title: String,
    subtitle: String,
    onClick: () -> Unit,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(start = 20.dp, end = 6.dp, top = 6.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(
            modifier = Modifier
                .weight(1f)
                .padding(vertical = 6.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyLarge,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (subtitle.isNotBlank()) {
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        if (actionLabel != null && onAction != null) {
            TextButton(onClick = onAction) {
                Text(actionLabel, style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
private fun LocalMessage(
    message: String,
    action: String?,
    onAction: (() -> Unit)?,
    contentPadding: PaddingValues,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(contentPadding),
        contentAlignment = Alignment.Center,
    ) {
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

/**
 * The directories whose tracks are kept out of the app.
 *
 * Stored as full paths, the same string [folderPath] derives and the same one
 * [LocalGroups.foldersOf] groups on, so a hidden folder stays hidden however
 * the device is rescanned or remounted. Plain SharedPreferences: this is a
 * preference, not library data, and it has to be readable before the first
 * listing finishes.
 */
private object HiddenFolders {
    private const val PREFS = "bitchord_hidden_folders"
    private const val KEY = "folders"

    private var loaded = false
    private val _hidden = MutableStateFlow<Set<String>>(emptySet())
    val hidden: StateFlow<Set<String>> = _hidden.asStateFlow()

    fun load(context: Context) {
        if (loaded) return
        loaded = true
        val stored = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getStringSet(KEY, emptySet())
            .orEmpty()
            .toSet()
        _hidden.value = stored
    }

    fun toggle(context: Context, path: String) {
        val next = if (path in _hidden.value) _hidden.value - path else _hidden.value + path
        _hidden.value = next
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putStringSet(KEY, next)
            .apply()
    }
}

/**
 * The directory a device file sits in, or null when its path isn't known.
 *
 * Deliberately identical to the one [LocalGroups.foldersOf] groups on: a hidden
 * path only matches the folder it came from if both sides derive it the same
 * way.
 */
private fun Song.folderPath(): String? =
    localPath?.replace('\\', '/')?.substringBeforeLast('/', "")?.takeIf { it.isNotEmpty() }

/** Whether this track sits in a folder the listener has hidden. */
private fun Song.isInHiddenFolder(hidden: Set<String>): Boolean =
    hidden.isNotEmpty() && folderPath()?.let { it in hidden } == true
"""


def edit(path, old, new, count=1):
    EDITS.append((path, old, new, count))


MAIN = "app/src/main/java/com/music/bitchord/MainActivity.kt"
VM = "app/src/main/java/com/music/bitchord/ui/MainViewModel.kt"
REG = "app/src/main/java/com/music/bitchord/data/sources/SourceRegistry.kt"
SRC_SCREEN = "app/src/main/java/com/music/bitchord/ui/screens/SourcesScreen.kt"

# --- MainActivity: import the new screen -------------------------------------
edit(MAIN,
     "import com.music.bitchord.ui.screens.LocalFolderTab",
     "import com.music.bitchord.ui.screens.LocalFolderTab\nimport com.music.bitchord.ui.screens.LocalHomeScreen")

# --- MainActivity: read the device's music, and stop loading the feed --------
edit(MAIN,
     "    var selectedTab by rememberSaveable { mutableIntStateOf(0) }",
     "    var selectedTab by rememberSaveable { mutableIntStateOf(0) }\n"
     "    // Local-only build: the device's own music, for the three tabs below.\n"
     "    val localSongs by viewModel.allLibrarySongs.collectAsStateWithLifecycle()")

edit(MAIN,
     """    LaunchedEffect(selectedTab) {
        if (selectedTab == TAB_EXPLORE) viewModel.onExploreShown()
    }""",
     """    LaunchedEffect(Unit) {
        // Local-only build: nothing catalogue-side is loaded; the tabs read the
        // device instead.
        viewModel.loadLibrarySongs()
    }""")

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

# --- MainActivity: four local tabs -------------------------------------------
edit(MAIN,
     """    val tabs = remember(homeLabel, exploreLabel, libraryLabel, searchLabel) {
        listOf(
            BottomTab(homeLabel, BitChordIcons.Home),
            BottomTab(exploreLabel, BitChordIcons.TabExplore),
            BottomTab(libraryLabel, BitChordIcons.TabLibrary),
            BottomTab(searchLabel, BitChordIcons.TabSearch),
        )
    }""",
     """    val songsLabel = stringResource(R.string.songs)
    val albumsLabel = stringResource(R.string.albums)
    val playlistsLabel = stringResource(R.string.playlists)
    val foldersLabel = stringResource(R.string.folders)
    // Local-only build: Songs, Albums, Playlists and Folders, all off the device.
    val tabs = remember(songsLabel, albumsLabel, playlistsLabel, foldersLabel) {
        listOf(
            BottomTab(songsLabel, BitChordIcons.Home),
            BottomTab(albumsLabel, BitChordIcons.GridView),
            BottomTab(playlistsLabel, BitChordIcons.TabLibrary),
            BottomTab(foldersLabel, BitChordIcons.TabExplore),
        )
    }""")

# --- MainActivity: draw the local screen for those four tabs -----------------
edit(MAIN,
     "                        } else when ((destination as? AppDestination.Tab)?.index ?: selectedTab) {",
     """                        } else if (route == null && detail == null && selectedTab <= TAB_SEARCH) {
                            // Local-only build: the device's own music, drawn by
                            // LocalHomeScreen rather than a catalogue feed.
                            LocalHomeScreen(
                                tab = selectedTab,
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
                        } else when ((destination as? AppDestination.Tab)?.index ?: selectedTab) {""")

# --- MainActivity: no search field or keyboard on the fourth tab --------------
# The bar's search accessory and its focus request were keyed on TAB_SEARCH,
# which is now the Folders tab. Both are switched off for this build.
edit(MAIN,
     "                        selectedTab == TAB_SEARCH && route == null && detail == null && selectedMoodGenre == null",
     "                        false && selectedTab == TAB_SEARCH && route == null && detail == null && selectedMoodGenre == null")

edit(MAIN,
     "                    if (index == TAB_SEARCH) {",
     "                    if (false && index == TAB_SEARCH) {")

# --- MainViewModel: expose the device listing, and stop the launch feed ------
edit(VM,
     "    private val _librarySongs = MutableStateFlow<UiState<List<Song>>>(UiState.Loading)",
     "    private val _librarySongs = MutableStateFlow<UiState<List<Song>>>(UiState.Loading)\n\n"
     "    /** The same listing, for the local-only tabs that draw the whole folder. */\n"
     "    val allLibrarySongs: StateFlow<UiState<List<Song>>> = _librarySongs.asStateFlow()")

edit(VM,
     """        startTypeaheadMediaPipeline()
        loadHome()""",
     """        startTypeaheadMediaPipeline()
        // Local-only build: the home feed is not loaded at launch.""")

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
