#include "cubiomes/generator.h"
#include "cubiomes/finders.h"
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <math.h>

#ifdef _WIN32
#define CUBIOMES_EXPORT __declspec(dllexport)
#else
#define CUBIOMES_EXPORT
#endif



CUBIOMES_EXPORT int INTERFACE_getSurfaceHeightEnd(int mcVersion, uint64_t seed, int x, int z){
    int y = getEndSurfaceHeight(mcVersion, seed, x, z);
    return y;
}


CUBIOMES_EXPORT int* INTERFACE_getStructurePos(int structuretype, int mcVersion, uint64_t seed, int rx, int rz)
{
    Pos pos;

    if (getStructurePos(structuretype, mcVersion, seed, rx, rz, &pos))
    {
    int* posArray = (int*)malloc(2 * sizeof(int));
    posArray[0] = pos.x;
    posArray[1] = pos.z;
    return posArray;
    }

    int* posArray = (int*)malloc(2 * sizeof(int));
    posArray[0] = 0;
    posArray[1] = 0;
    return posArray;
}

CUBIOMES_EXPORT int INTERFACE_isViableStructurePos(int structuretype, int mcVersion, uint64_t seed, int dimension, int x, int z){
    Generator g;
    setupGenerator(&g, mcVersion, 0);
    applySeed(&g, dimension, seed);

    return isViableStructurePos(structuretype, &g, x, z, 0);
}

CUBIOMES_EXPORT int* INTERFACE_getStrongholdPos(uint64_t seed, int mcVersion, int count){
    Generator g;
    setupGenerator(&g, mcVersion, 0);
    applySeed(&g, DIM_OVERWORLD, seed);
    StrongholdIter sh;
    Pos pos = initFirstStronghold(&sh, mcVersion, seed);

    int* StrongholdPositions = (int*) malloc(128 * 2 * sizeof(int));
    
    for (int i = 0; i < count; i++){
        nextStronghold(&sh, &g);
        StrongholdPositions[i * 2] = sh.pos.x; // Store x position
        StrongholdPositions[i * 2 + 1] = sh.pos.z; // Store z position
    }
    return StrongholdPositions;
}


CUBIOMES_EXPORT int* INTERFACE_getSpwan(uint64_t seed, int mcVersion){
    Generator g;
    setupGenerator(&g, mcVersion, 0);
    applySeed(&g, DIM_OVERWORLD, seed);
    Pos pos = getSpawn(&g);
    int* position = (int*)malloc(2*sizeof(int));
    position[0] = pos.x;
    position[1] = pos.z;
    return position;
}

CUBIOMES_EXPORT int INTERFACE_getBiomeAt(int mcVersion, uint64_t seed, int dimension, int x, int y, int z){
    Generator g;
    setupGenerator(&g, mcVersion, 0);
    applySeed(&g, dimension, seed);
    int biome = getBiomeAt(&g, 1, x, y, z);
    return biome;
}


CUBIOMES_EXPORT int INTERFACE_getBastionVariant(int mcVersion, uint64_t seed, int x, int z){
    StructureVariant sv;
    int bastion_type = getVariant(&sv, Bastion, mcVersion, seed, x, z, -1);
    
    switch (sv.sx)
    {
    case 46: {return 0;}  // Housing
    case 30: {return 1;}  // Stables
    case 38: {return 2;}  // Treasure
    case 16: {return 3;}  // Bridge
    default: {return -1;}
    }
}


CUBIOMES_EXPORT int** INTERFACE_find_in_range(int structure, int mcVersion, uint64_t seed, int dimension, int srx, int srz, int erx, int erz){
    int **array;
    int xlen = abs(srx-erx);
    int zlen = abs(srz-erz);

    array = (int **)malloc((xlen*zlen + 1) * sizeof(int *));
    for(int i = 0; i < (xlen*zlen + 1); i++) {
        array[i] = (int *)malloc(2 * sizeof(int));
    }

    int counter = 1;
    Generator g;

    setupGenerator(&g, mcVersion, 0);
    applySeed(&g, dimension, seed);

    for (int rx = srx; rx<erx;rx++){
        for (int rz = srz; rz<erz;rz++){
            Pos pos;
            if (getStructurePos(structure, mcVersion, seed, rx, rz, &pos)){
                if (isViableStructurePos(structure, &g, pos.x, pos.z, 0)){
                    
                    array[counter][0] = pos.x;
                    array[counter][1] = pos.z;
                    counter++;

                }
            }
        }
    }
    array[0][0] = counter;
    return array;
}


// Find the nearest viable structure to a block-coordinate center (cx, cz),
// where `limit` is the maximum search radius in BLOCKS.
//
// The previous implementation mixed block coordinates (center) with region
// indices, which made any non-origin search return garbage or nothing. This
// version converts the center to region coordinates using the version-specific
// region size, walks region rings outward, and keeps the closest viable hit by
// true block distance. It fails fast: once no unexplored region ring can
// possibly hold a structure within `limit` (or closer than the best hit so
// far), the search stops.
CUBIOMES_EXPORT int* INTERFACE_find_closest_structure(int structure, int mcVersion, uint64_t seed, int dimension, int cx, int cz, int limit){
    int* posArray = (int*)malloc(2 * sizeof(int));
    posArray[0] = 0;
    posArray[1] = 0;

    StructureConfig sconf;
    if (!getStructureConfig(structure, mcVersion, &sconf))
        return posArray;

    int regBlocks = (int)sconf.regionSize * 16; // region edge length in blocks
    if (regBlocks <= 0)
        return posArray;

    Generator g;
    setupGenerator(&g, mcVersion, 0);
    applySeed(&g, dimension, seed);

    // Center region (floor division, correct for negatives).
    int centerRegX = (cx >= 0) ? (cx / regBlocks) : -(((-cx) + regBlocks - 1) / regBlocks);
    int centerRegZ = (cz >= 0) ? (cz / regBlocks) : -(((-cz) + regBlocks - 1) / regBlocks);

    // Region rings needed to cover `limit` blocks, plus margin: a structure can
    // sit anywhere inside its region, so add 2 rings of slack.
    int maxRing = (limit / regBlocks) + 2;

    long long limit2 = (long long)limit * (long long)limit;
    long long bestDist2 = -1;
    int bestX = 0, bestZ = 0;
    int found = 0;

    for (int ring = 0; ring <= maxRing; ring++){
        // The closest a structure in this ring (or any further ring) can be to
        // the center is at least (ring-1) full regions away.
        long long ringFloor = (long long)(ring - 1) * (long long)regBlocks;
        if (ring >= 1 && ringFloor > 0){
            if (ringFloor * ringFloor > limit2) break;              // nothing left within limit
            if (found && ringFloor * ringFloor >= bestDist2) break; // can't beat current best
        }

        for (int rx = centerRegX - ring; rx <= centerRegX + ring; rx++){
            for (int rz = centerRegZ - ring; rz <= centerRegZ + ring; rz++){
                // Only walk the border of the current ring.
                if (ring != 0 &&
                    rx != centerRegX - ring && rx != centerRegX + ring &&
                    rz != centerRegZ - ring && rz != centerRegZ + ring)
                    continue;

                Pos loc;
                if (!getStructurePos(structure, mcVersion, seed, rx, rz, &loc))
                    continue;

                long long dxb = (long long)loc.x - (long long)cx;
                long long dzb = (long long)loc.z - (long long)cz;
                long long d2 = dxb * dxb + dzb * dzb;

                if (d2 > limit2)
                    continue;
                if (found && d2 >= bestDist2)
                    continue;
                if (!isViableStructurePos(structure, &g, loc.x, loc.z, 0))
                    continue;

                bestDist2 = d2;
                bestX = loc.x;
                bestZ = loc.z;
                found = 1;
            }
        }
    }

    if (found){
        posArray[0] = bestX;
        posArray[1] = bestZ;
    }
    return posArray;
}

CUBIOMES_EXPORT int INTERFACE_getVariant(
    StructureVariant *sv,
    int structType,
    int mc,
    uint64_t seed,
    int x,
    int z,
    int biome_id)
{
    return getVariant(sv, structType, mc, seed, x, z, biome_id);
}

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved)
{
    (void)hinstDLL;
    (void)fdwReason;
    (void)lpvReserved;
    return TRUE;
}
#endif
