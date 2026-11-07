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
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.music.bitchord.data.model.Song
import com.music.bitchord.data.model.UiState
import com.music.bitchord.data.settings.LocalMusicSort
import com.music.bitchord.sharedui.resources.Res as SharedRes
import com.music.bitchord.sharedui.resources.ic_logo
import com.music.bitchord.ui.components.SongRow
import org.jetbrains.compose.resources.painterResource

/**
 * Local-only build: the home tab is every track on the device, under the app's
 * mark where the original home carried it — no page header, no artwork, no
 * Play/Shuffle block, because those belong to the release page Albums and
 * Library show.
 *
 * The row at the top carries the same two controls the release page's bar does:
 * a way into search, and the ordering. Both are real — the sort reorders this
 * list, and search moves to the search tab — rather than drawn to look right.
 */
@Composable
fun LocalSongsScreen(
    songsState: UiState<List<Song>>,
    contentPadding: PaddingValues,
    onPlay: (List<Song>, Int) -> Unit,
    onRequestPermission: () -> Unit,
    onSearch: () -> Unit,
) {
    val songs = (songsState as? UiState.Success<List<Song>>)?.data.orEmpty()
    var sort by rememberSaveable { mutableStateOf(LocalMusicSort.TITLE_ASC) }
    var sortMenuOpen by remember { mutableStateOf(false) }

    val sorted = remember(songs, sort) {
        when (sort) {
            LocalMusicSort.TITLE_ASC -> songs.sortedBy { it.title.lowercase() }
            LocalMusicSort.TITLE_DESC -> songs.sortedByDescending { it.title.lowercase() }
            LocalMusicSort.DATE_ADDED -> songs.sortedByDescending { it.localDateAddedSeconds ?: 0L }
            LocalMusicSort.DATE_MODIFIED -> songs.sortedByDescending { it.localDateModifiedSeconds ?: 0L }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                // The bar's own band, not the content inset: the mark belongs up
                // beside the account button, not below the space reserved for it.
                .statusBarsPadding()
                .padding(start = 20.dp, end = 8.dp, top = 4.dp, bottom = 2.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(modifier = Modifier.weight(1f)) {
                Icon(
                    painter = painterResource(SharedRes.drawable.ic_logo),
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onBackground,
                    modifier = Modifier
                        .height(30.dp)
                        .aspectRatio(730f / 484f),
                )
            }
            IconButton(onClick = onSearch) {
                Icon(
                    imageVector = Icons.Rounded.Search,
                    contentDescription = "Search",
                    tint = MaterialTheme.colorScheme.onBackground,
                )
            }
            Box {
                IconButton(onClick = { sortMenuOpen = true }) {
                    Icon(
                        imageVector = Icons.Rounded.Tune,
                        contentDescription = "Sort",
                        tint = MaterialTheme.colorScheme.onBackground,
                    )
                }
                DropdownMenu(
                    expanded = sortMenuOpen,
                    onDismissRequest = { sortMenuOpen = false },
                ) {
                    LocalMusicSort.entries.forEach { option ->
                        DropdownMenuItem(
                            text = { Text(option.label()) },
                            onClick = {
                                sort = option
                                sortMenuOpen = false
                            },
                        )
                    }
                }
            }
        }

        when {
            songsState is UiState.Error -> LocalSongsMessage(
                message = songsState.message,
                action = "Allow access",
                onAction = onRequestPermission,
                contentPadding = contentPadding,
            )
            songsState is UiState.Loading -> LocalSongsMessage(
                message = "Reading your music...",
                action = null,
                onAction = null,
                contentPadding = contentPadding,
            )
            sorted.isEmpty() -> LocalSongsMessage(
                message = "No music yet. Point Local music folder at your files in Settings.",
                action = null,
                onAction = null,
                contentPadding = contentPadding,
            )
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = contentPadding.calculateBottomPadding()),
            ) {
                itemsIndexed(sorted, key = { _, song -> song.videoId }) { index, song ->
                    SongRow(song = song, onClick = { onPlay(sorted, index) })
                }
            }
        }
    }
}

private fun LocalMusicSort.label(): String = when (this) {
    LocalMusicSort.TITLE_ASC -> "Title A to Z"
    LocalMusicSort.TITLE_DESC -> "Title Z to A"
    LocalMusicSort.DATE_ADDED -> "Date added"
    LocalMusicSort.DATE_MODIFIED -> "Date modified"
}

@Composable
private fun LocalSongsMessage(
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
"""
NEW_HIDDEN_PATH = "app/src/main/java/com/music/bitchord/data/HiddenFolders.kt"
NEW_HIDDEN = r"""package com.music.bitchord.data

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Local-only build: the directories whose tracks are kept out of the app.
 *
 * Stored as full paths — the same string the scan derives and the same one
 * [LocalGroups] groups on — so a hidden folder stays hidden across rescans,
 * reboots and a card being remounted under the same name.
 *
 * A folder is hidden by its own path, never by a song id, so everything that
 * reads the device listing loses it at once: the song list, the album and
 * artist groupings, the playlists built from those files, and search.
 */
object HiddenFolders {
    private const val PREFS = "bitchord_hidden_folders"
    private const val KEY = "folders"

    private var loaded = false
    private val _hidden = MutableStateFlow<Set<String>>(emptySet())
    val hidden: StateFlow<Set<String>> = _hidden.asStateFlow()

    fun init(context: Context) {
        if (loaded) return
        loaded = true
        _hidden.value = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getStringSet(KEY, emptySet())
            .orEmpty()
            .toSet()
    }

    /** Whether the directory holding [path] is hidden. */
    fun isHiddenPath(path: String?): Boolean {
        val hidden = _hidden.value
        if (hidden.isEmpty() || path == null) return false
        val directory = path.replace('\\', '/').substringBeforeLast('/', "")
        return directory.isNotEmpty() && directory in hidden
    }

    fun hide(context: Context, directory: String) {
        val next = _hidden.value + directory
        _hidden.value = next
        persist(context, next)
    }

    /**
     * Brings every hidden folder back.
     *
     * One at a time would need the hidden folders listed somewhere to choose
     * from, and the only screen that could list them is the one they were
     * hidden from. Restoring them all is the way out that cannot be lost.
     */
    fun unhideAll(context: Context) {
        _hidden.value = emptySet()
        persist(context, emptySet())
    }

    private fun persist(context: Context, value: Set<String>) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putStringSet(KEY, value)
            .apply()
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
                                onSearch = {
                                    selectedTab = TAB_SEARCH
                                    viewModel.loadLibrarySongs()
                                    searchFocusRequested = true
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

# --- The Local Music page drops its header on Albums and Library -------------
edit("app/src/main/java/com/music/bitchord/ui/screens/DetailScreen.kt",
     """    folder: LocalFolder? = null,""",
     """    folder: LocalFolder? = null,
    /**
     * Local-only build: drops the release header, leaving the folder's own tabs
     * at the top of the page. The Albums and Library tabs are the device's own
     * music, and the "Local Music" sleeve above them is one thing too many
     * between the tab bar and the albums it is showing.
     */
    hideHeader: Boolean = false,""")

edit("app/src/main/java/com/music/bitchord/ui/screens/DetailScreen.kt",
     "            item(key = \"header\") {",
     "            if (!hideHeader) item(key = \"header\") {")

edit("app/src/main/java/com/music/bitchord/ui/screens/DetailScreen.kt",
     """            if (searching) {
                item(key = \"search\") {""",
     """            // With the header gone, the first item has to clear the bar itself.
            if (hideHeader) {
                item(key = \"top-inset\") {
                    Spacer(Modifier.height(contentPadding.calculateTopPadding()))
                }
            }

            if (searching) {
                item(key = \"search\") {""")

edit(MAIN,
     """                                songSort = songSort,
                                folder = folder,""",
     """                                songSort = songSort,
                                folder = folder,
                                // Local-only build: Albums and Library show the
                                // device's own groupings, not a release header.
                                hideHeader = page.browseId == \"local:all\" &&
                                    (selectedTab == TAB_EXPLORE || selectedTab == TAB_LIBRARY),""")

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

# --- Hidden folders: the store, the filter, and the way back ----------------
edit("app/src/main/java/com/music/bitchord/BitChordApplication.kt",
     "import com.music.bitchord.data.DebugLog",
     "import com.music.bitchord.data.DebugLog\nimport com.music.bitchord.data.HiddenFolders")

edit("app/src/main/java/com/music/bitchord/BitChordApplication.kt",
     "        AppSettings.init(this, authStore)",
     "        AppSettings.init(this, authStore)\n        HiddenFolders.init(this)")

# The scan is the one place every listing comes from, so hiding here takes the
# folder out of the songs, the album and artist groupings, the playlists built
# from those files, and search at once.
edit("app/src/main/java/com/music/bitchord/data/LocalMediaRepository.kt",
     "                    if (filterNonMusic && !isEligibleLocalMusic(durationMs, displayName, path)) continue",
     "                    if (filterNonMusic && !isEligibleLocalMusic(durationMs, displayName, path)) continue\n"
     "                    if (HiddenFolders.isHiddenPath(path)) continue")

edit("app/src/main/java/com/music/bitchord/ui/components/BrowseActionsMenu.kt",
     """    isPinned: Boolean = false,
    onTogglePin: (() -> Unit)? = null,""",
     """    isPinned: Boolean = false,
    onTogglePin: (() -> Unit)? = null,
    /**
     * Local-only build: hides the device folder this grouping came from. Set
     * only for a folder on the Local Music page.
     */
    onHideFolder: (() -> Unit)? = null,""")

edit("app/src/main/java/com/music/bitchord/ui/components/BrowseActionsMenu.kt",
     "            onDownloadAll?.let { download ->",
     """            onHideFolder?.let { hide ->
                ActionRow(SfIcons.VisibilityOff, "Hide folder", onClick = hide)
            }
            onDownloadAll?.let { download ->""")

edit(MAIN,
     "import com.music.bitchord.data.LocalGroups",
     "import com.music.bitchord.data.LocalGroups\nimport com.music.bitchord.data.HiddenFolders")

edit(MAIN,
     "    val localSongs by viewModel.allLibrarySongs.collectAsStateWithLifecycle()",
     "    val localSongs by viewModel.allLibrarySongs.collectAsStateWithLifecycle()\n"
     "    val hiddenFolders by HiddenFolders.hidden.collectAsStateWithLifecycle()")

edit(MAIN,
     """            BrowseActionsMenu(
                // The live answer, not the one the target was built with.""",
     """            BrowseActionsMenu(
                onHideFolder = if (target.browseId?.startsWith("local:group:folder:") == true) {
                    {
                        val directory = target.songs.firstOrNull()
                            ?.localPath
                            ?.substringBeforeLast('/', "")
                            ?.takeIf { it.isNotEmpty() }
                        if (directory != null) {
                            HiddenFolders.hide(context, directory)
                            viewModel.reloadLocalDetail("local:all")
                            viewModel.loadLibrarySongs()
                        }
                    }
                } else {
                    null
                },
                // The live answer, not the one the target was built with.""")

edit(MAIN,
     "                                    onCreatePlaylist = if (isDevice) ({ creatingOfflinePlaylist = true }) else null,",
     """                                    onCreatePlaylist = if (isDevice) ({ creatingOfflinePlaylist = true }) else null,
                                    hiddenFolderCount = hiddenFolders.size,
                                    onUnhideAllFolders = {
                                        HiddenFolders.unhideAll(context)
                                        viewModel.reloadLocalDetail("local:all")
                                        viewModel.loadLibrarySongs()
                                    },""")

edit("app/src/main/java/com/music/bitchord/ui/screens/LocalFolder.kt",
     """    /** Puts "New playlist" at the head of the Playlists tab. */
    val onCreatePlaylist: (() -> Unit)? = null,""",
     """    /** Puts "New playlist" at the head of the Playlists tab. */
    val onCreatePlaylist: (() -> Unit)? = null,
    /** Local-only build: how many folders are hidden, for the way back. */
    val hiddenFolderCount: Int = 0,
    /** Local-only build: brings every hidden folder back. */
    val onUnhideAllFolders: (() -> Unit)? = null,""")

edit("app/src/main/java/com/music/bitchord/ui/screens/LocalFolder.kt",
     """    if (state.tab == LocalFolderTab.PLAYLISTS && query.isBlank()) {
        folder.onCreatePlaylist?.let { create ->
            item(key = "folder-new-playlist") {
                NewPlaylistRow(palette, onClick = create)
                FolderDivider(palette)
            }
        }
    }""",
     """    if (state.tab == LocalFolderTab.PLAYLISTS && query.isBlank()) {
        folder.onCreatePlaylist?.let { create ->
            item(key = "folder-new-playlist") {
                NewPlaylistRow(palette, onClick = create)
                FolderDivider(palette)
            }
        }
    }

    // Local-only build: the way back from hiding a folder. It lives on this tab
    // because this is where folders are, and it is the only place a hidden one
    // could be brought back from.
    if (state.tab == LocalFolderTab.FOLDERS && folder.hiddenFolderCount > 0) {
        folder.onUnhideAllFolders?.let { unhide ->
            item(key = "folder-unhide") {
                UnhideFoldersRow(palette, folder.hiddenFolderCount, onClick = unhide)
                FolderDivider(palette)
            }
        }
    }""")

edit("app/src/main/java/com/music/bitchord/ui/screens/LocalFolder.kt",
     "private fun NewPlaylistRow(palette: ArtworkPalette, onClick: () -> Unit) {",
     """private fun UnhideFoldersRow(palette: ArtworkPalette, count: Int, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = PAGE_GUTTER, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = if (count == 1) {
                "1 hidden folder - tap to show it again"
            } else {
                "$count hidden folders - tap to show them again"
            },
            style = MaterialTheme.typography.bodyMedium,
            color = palette.accent,
        )
    }
}

@Composable
private fun NewPlaylistRow(palette: ArtworkPalette, onClick: () -> Unit) {""")

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

    hidden = ROOT / NEW_HIDDEN_PATH
    hidden.parent.mkdir(parents=True, exist_ok=True)
    hidden.write_text(NEW_HIDDEN, encoding="utf-8")
    print("ok    added", NEW_HIDDEN_PATH)

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
